"""
Self-Correction Loop for SQL Query Generation

This module implements an iterative error correction system that:
1. Executes generated SQL queries
2. Catches syntax and runtime errors
3. Feeds error messages back to the LLM
4. Regenerates the query with corrections
5. Repeats until success or max retries reached
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from ..core.llm import get_llm
from ..core.config import settings

logger = logging.getLogger(__name__)


class SQLExecutionResult:
    """Result of SQL query execution attempt."""
    
    def __init__(
        self,
        success: bool,
        sql_query: str,
        error_message: Optional[str] = None,
        row_count: Optional[int] = None,
        execution_time_ms: Optional[float] = None
    ):
        self.success = success
        self.sql_query = sql_query
        self.error_message = error_message
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.timestamp = datetime.utcnow()


class CorrectionAttempt:
    """Record of a single correction attempt."""
    
    def __init__(
        self,
        attempt_number: int,
        sql_query: str,
        error_message: Optional[str],
        success: bool
    ):
        self.attempt_number = attempt_number
        self.sql_query = sql_query
        self.error_message = error_message
        self.success = success
        self.timestamp = datetime.utcnow()


class SelfCorrectingAgent:
    """
    Agent that can generate SQL and iteratively fix errors through execution feedback.
    
    This implements the self-correction loop described in the resume:
    - Executes generated SQL
    - Catches errors
    - Feeds error back to LLM
    - Regenerates query with fixes
    - Repeats until success or max attempts
    """
    
    def __init__(self, max_attempts: int = 3):
        """
        Initialize the self-correcting agent.
        
        Args:
            max_attempts: Maximum number of correction attempts
        """
        self.max_attempts = max_attempts
        self.llm = get_llm()
        self.correction_history: List[CorrectionAttempt] = []
        
        # Prompt for initial SQL generation
        self.initial_prompt = ChatPromptTemplate.from_template("""
You are an expert SQL writer. Generate a clean, efficient, and executable SQL query.

**SQL Dialect:** PostgreSQL

**Database Schema:**
```sql
{schema}
```

**User Question:**
{question}

**Structured Plan:**
```json
{plan}
```

**Instructions:**
- Generate a single, executable SQL query
- Do not add explanations or comments
- Ensure correct PostgreSQL syntax
- Use proper JOINs, WHERE clauses, and aggregations as needed
        """)
        
        # Prompt for error correction
        self.correction_prompt = ChatPromptTemplate.from_template("""
You are an expert SQL debugger. Fix the SQL query that produced an error.

**SQL Dialect:** PostgreSQL

**Database Schema:**
```sql
{schema}
```

**User Question:**
{question}

**Failed SQL Query:**
```sql
{failed_query}
```

**Error Message:**
```
{error_message}
```

**Previous Attempts:**
{previous_attempts}

**Instructions:**
- Analyze the error message carefully
- Fix the SQL query to resolve the error
- Generate ONLY the corrected SQL query
- Do not repeat the same mistake from previous attempts
- Ensure the query answers the original user question
        """)
        
        logger.info(f"SelfCorrectingAgent initialized with max_attempts={max_attempts}")
    
    def execute_sql(self, sql_query: str) -> SQLExecutionResult:
        """
        Execute SQL query and return result or error.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            SQLExecutionResult with success status and details
        """
        if not settings.database_url or settings.database_url == "your_database_url_here":
            logger.warning("No database configured for execution")
            return SQLExecutionResult(
                success=False,
                sql_query=sql_query,
                error_message="No database configured for SQL execution"
            )
        
        import time
        start_time = time.time()
        
        try:
            engine = create_engine(settings.database_url)
            
            with engine.connect() as connection:
                # Execute query in a transaction that gets rolled back
                with connection.begin() as transaction:
                    result = connection.execute(text(sql_query))
                    
                    # For SELECT queries, count rows
                    row_count = None
                    if sql_query.strip().upper().startswith('SELECT'):
                        rows = result.fetchall()
                        row_count = len(rows)
                    
                    # Always rollback to prevent any modifications
                    transaction.rollback()
                    
                    execution_time = (time.time() - start_time) * 1000
                    
                    logger.info(f"SQL executed successfully in {execution_time:.2f}ms")
                    
                    return SQLExecutionResult(
                        success=True,
                        sql_query=sql_query,
                        row_count=row_count,
                        execution_time_ms=execution_time
                    )
        
        except SQLAlchemyError as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            logger.warning(f"SQL execution failed: {error_msg}")
            
            return SQLExecutionResult(
                success=False,
                sql_query=sql_query,
                error_message=error_msg,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Unexpected error during SQL execution: {e}")
            
            return SQLExecutionResult(
                success=False,
                sql_query=sql_query,
                error_message=str(e),
                execution_time_ms=execution_time
            )
    
    def generate_initial_sql(
        self,
        schema: str,
        question: str,
        plan: Dict[str, Any]
    ) -> str:
        """
        Generate initial SQL query from plan.
        
        Args:
            schema: Database schema
            question: User's question
            plan: Structured query plan
            
        Returns:
            Generated SQL query
        """
        chain = self.initial_prompt | self.llm | StrOutputParser()
        
        sql_query = chain.invoke({
            "schema": schema,
            "question": question,
            "plan": plan
        })
        
        return sql_query.strip()
    
    def correct_sql(
        self,
        schema: str,
        question: str,
        failed_query: str,
        error_message: str,
        attempt_number: int
    ) -> str:
        """
        Generate corrected SQL query based on error feedback.
        
        Args:
            schema: Database schema
            question: User's question
            failed_query: SQL query that failed
            error_message: Error message from failed execution
            attempt_number: Current attempt number
            
        Returns:
            Corrected SQL query
        """
        # Build previous attempts summary
        previous_attempts = "\n".join([
            f"Attempt {att.attempt_number}: {att.error_message or 'Success'}"
            for att in self.correction_history[-3:]  # Last 3 attempts
        ]) or "None"
        
        chain = self.correction_prompt | self.llm | StrOutputParser()
        
        corrected_query = chain.invoke({
            "schema": schema,
            "question": question,
            "failed_query": failed_query,
            "error_message": error_message,
            "previous_attempts": previous_attempts
        })
        
        return corrected_query.strip()
    
    def generate_with_correction(
        self,
        schema: str,
        question: str,
        plan: Dict[str, Any]
    ) -> Tuple[str, bool, List[CorrectionAttempt]]:
        """
        Generate SQL with self-correction loop.
        
        This is the main method implementing the correction loop:
        1. Generate initial SQL
        2. Execute it
        3. If error, regenerate with error feedback
        4. Repeat until success or max attempts
        
        Args:
            schema: Database schema
            question: User's question
            plan: Structured query plan
            
        Returns:
            Tuple of (final_sql_query, success, correction_history)
        """
        self.correction_history = []
        
        logger.info(f"Starting self-correction loop (max attempts: {self.max_attempts})")
        
        # Attempt 1: Initial generation
        current_sql = self.generate_initial_sql(schema, question, plan)
        
        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Attempt {attempt}/{self.max_attempts}: Executing SQL...")
            
            # Execute SQL
            result = self.execute_sql(current_sql)
            
            # Record attempt
            attempt_record = CorrectionAttempt(
                attempt_number=attempt,
                sql_query=current_sql,
                error_message=result.error_message,
                success=result.success
            )
            self.correction_history.append(attempt_record)
            
            if result.success:
                logger.info(
                    f"✅ SQL executed successfully on attempt {attempt}"
                    f"{f' ({result.row_count} rows)' if result.row_count is not None else ''}"
                )
                return current_sql, True, self.correction_history
            
            # If failed and not last attempt, try to correct
            if attempt < self.max_attempts:
                logger.warning(
                    f"❌ Attempt {attempt} failed: {result.error_message[:100]}..."
                )
                logger.info(f"Generating correction (attempt {attempt + 1})...")
                
                # Generate corrected query
                current_sql = self.correct_sql(
                    schema=schema,
                    question=question,
                    failed_query=current_sql,
                    error_message=result.error_message,
                    attempt_number=attempt + 1
                )
            else:
                logger.error(
                    f"❌ All {self.max_attempts} attempts failed. "
                    f"Final error: {result.error_message}"
                )
        
        # All attempts failed
        return current_sql, False, self.correction_history


def get_self_correcting_agent(max_attempts: int = 3) -> SelfCorrectingAgent:
    """
    Get a self-correcting agent instance.
    
    Args:
        max_attempts: Maximum correction attempts
        
    Returns:
        SelfCorrectingAgent instance
    """
    return SelfCorrectingAgent(max_attempts=max_attempts)
