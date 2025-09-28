import logging
import re
from typing import Tuple, Optional
from functools import lru_cache

from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from ..core.config import settings

logger = logging.getLogger(__name__)

class SQLValidationError(Exception):
    """Raised when SQL validation fails."""
    pass

# Dangerous SQL patterns that should be blocked
DANGEROUS_PATTERNS = [
    r'\bDROP\s+TABLE\b',
    r'\bDELETE\s+FROM\b',
    r'\bTRUNCATE\s+TABLE\b',
    r'\bINSERT\s+INTO\b',
    r'\bUPDATE\s+SET\b',
    r'\bALTER\s+TABLE\b',
    r'\bCREATE\s+TABLE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
]

@lru_cache(maxsize=1)
def get_validation_engine() -> Optional[Engine]:
    """
    Get a cached SQLAlchemy engine for validation.

    Returns:
        Engine instance or None if no database URL is configured
    """
    if not settings.database_url or settings.database_url == "your_database_url_here":
        logger.info("No database URL configured, SQL validation will be skipped")
        return None

    try:
        # Use NullPool to avoid connection pooling for validation
        engine = create_engine(
            settings.database_url,
            poolclass=NullPool,
            echo=False,
            connect_args={"connect_timeout": 10}
        )
        logger.info("SQL validation engine initialized")
        return engine
    except Exception as e:
        logger.error(f"Failed to create validation engine: {e}")
        return None

def is_safe_query(sql_query: str) -> Tuple[bool, str]:
    """
    Check if the SQL query contains dangerous patterns.

    Args:
        sql_query: The SQL query to check

    Returns:
        Tuple of (is_safe, message)
    """
    query_upper = sql_query.upper()

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query_upper, re.IGNORECASE):
            return False, f"Query contains potentially dangerous operation: {pattern}"

    return True, "Query passed safety check"

def validate_sql_syntax(sql_query: str) -> Tuple[bool, str]:
    """
    Validate SQL syntax by executing it in a read-only transaction.

    Args:
        sql_query: The SQL query string to validate

    Returns:
        Tuple of (is_valid, message)
    """
    engine = get_validation_engine()
    if not engine:
        return False, "No database configured for validation"

    try:
        with engine.connect() as connection:
            # Execute in a transaction that gets rolled back
            with connection.begin() as transaction:
                # Set the connection to read-only mode if supported
                try:
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                except SQLAlchemyError:
                    # Some databases don't support this, continue anyway
                    pass

                # Execute the query
                result = connection.execute(text(sql_query))

                # For SELECT queries, fetch one row to ensure the query is complete
                if sql_query.strip().upper().startswith('SELECT'):
                    try:
                        result.fetchone()
                    except Exception:
                        pass  # Empty result sets are fine

                # Always rollback to ensure no changes
                transaction.rollback()

        return True, "SQL syntax validation successful"

    except SQLAlchemyError as e:
        error_msg = str(e).split('\n')[0]  # Get first line of error
        logger.warning(f"SQL validation failed: {error_msg}")
        return False, f"SQL syntax error: {error_msg}"
    except Exception as e:
        logger.error(f"Unexpected error during SQL validation: {e}")
        return False, f"Validation error: {str(e)}"

def validate_sql_query(sql_query: str) -> Tuple[bool, str]:
    """
    Comprehensive SQL query validation including safety and syntax checks.

    This function performs both safety checks (to prevent dangerous operations)
    and syntax validation (by executing against a database if configured).

    Args:
        sql_query: The SQL query string to validate

    Returns:
        Tuple of (is_valid, message) where:
        - is_valid: True if query is safe and valid, False otherwise
        - message: Descriptive message about the validation result
    """
    if not sql_query or not sql_query.strip():
        return False, "Empty query provided"

    # Strip whitespace and ensure query doesn't end with semicolon
    sql_query = sql_query.strip().rstrip(';')

    logger.info(f"Validating SQL query: {sql_query[:100]}...")

    # First, check for dangerous patterns
    is_safe, safety_message = is_safe_query(sql_query)
    if not is_safe:
        logger.warning(f"Unsafe SQL query detected: {safety_message}")
        return False, safety_message

    # Then validate syntax if database is configured
    engine = get_validation_engine()
    if not engine:
        logger.info("Database validation skipped - no database configured")
        return True, "Safety check passed (database validation skipped)"

    return validate_sql_syntax(sql_query)

def clear_validation_cache():
    """Clear the validation engine cache. Useful for testing."""
    get_validation_engine.cache_clear()
    logger.info("Validation engine cache cleared")