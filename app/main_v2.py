"""
QueryScribeAI FastAPI Application (Enhanced Version)

This version includes:
- Schema-Aware RAG for intelligent schema retrieval
- Self-Correction Loop for iterative query fixing
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import QueryRequest, QueryResponse, ErrorResponse, ValidationStatus
from ..agents.analyzer_agent import get_analyzer_chain
from ..agents.explainer_agent import get_explainer_chain
from ..agents.self_correction import get_self_correcting_agent
from ..db.schema_rag import get_schema_rag, initialize_schema_rag

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QueryScribe AI (Enhanced)",
    description="Text-to-SQL with Schema-Aware RAG and Self-Correction Loop",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            details={"path": str(request.url.path)}
        ).dict()
    )

async def load_schema() -> str:
    """Load the sample schema file."""
    schema_path = Path(__file__).parent.parent / "data" / "sample_schema.sql"
    try:
        return schema_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail="No database schema provided and sample_schema.sql not found."
        )

@app.on_event("startup")
async def startup_event():
    """Initialize Schema RAG on startup."""
    logger.info("Initializing QueryScribeAI v2.0 with Schema-Aware RAG...")
    try:
        # Load and index sample schema
        schema = await load_schema()
        await asyncio.to_thread(initialize_schema_rag, schema)
        logger.info("✅ Schema-Aware RAG initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize RAG: {e}")

@app.post("/generate-sql", response_model=QueryResponse)
async def generate_sql(request: QueryRequest):
    """
    Enhanced endpoint with Schema-Aware RAG and Self-Correction Loop.
    
    Flow:
    1. Use RAG to retrieve relevant schema parts
    2. Analyze schema and question
    3. Generate SQL with self-correction loop
    4. Execute and iterate until success or max attempts
    5. Generate explanation
    """
    import time
    start_time = time.time()

    logger.info(f"📝 Processing question: {request.question[:100]}...")

    # Load schema if not provided
    db_schema = request.db_schema
    if not db_schema:
        db_schema = await load_schema()

    try:
        # Step 1: Schema-Aware RAG Retrieval
        logger.info("🔍 Retrieving relevant schema using RAG...")
        rag = get_schema_rag()
        
        # If RAG is initialized, use it
        rag_enabled = rag.schema_loaded
        tables_retrieved = 0
        
        if rag_enabled:
            # Retrieve relevant schema parts
            relevant_schema = await asyncio.to_thread(
                rag.retrieve_relevant_schema,
                request.question,
                top_k=5  # Get top 5 most relevant tables
            )
            
            if relevant_schema:
                # Use focused schema for better accuracy
                focused_schema = relevant_schema
                table_names = rag.get_all_table_names()
                tables_retrieved = len(relevant_schema.split("CREATE TABLE")) - 1
                logger.info(f"✅ Retrieved {tables_retrieved} relevant tables via RAG")
            else:
                # Fallback to full schema
                focused_schema = db_schema
                logger.info("⚠️ No relevant tables found, using full schema")
        else:
            # RAG not initialized, use full schema
            focused_schema = db_schema
            logger.info("ℹ️ RAG not initialized, using full schema")

        # Step 2: Schema & Intent Analysis
        logger.info("🧠 Analyzing schema and intent...")
        analyzer_chain = get_analyzer_chain()
        structured_plan = await asyncio.to_thread(
            analyzer_chain.invoke,
            {"schema": focused_schema, "user_question": request.question}
        )
        logger.info("✅ Analysis complete")

        # Step 3: SQL Generation with Self-Correction Loop
        logger.info("🔄 Starting self-correction loop...")
        correcting_agent = get_self_correcting_agent(max_attempts=3)
        
        final_sql, success, correction_history = await asyncio.to_thread(
            correcting_agent.generate_with_correction,
            schema=focused_schema,
            question=request.question,
            plan=structured_plan
        )
        
        num_attempts = len(correction_history)
        self_correction_applied = num_attempts > 1
        
        if success:
            logger.info(
                f"✅ SQL generated successfully "
                f"({'after ' + str(num_attempts) + ' attempts' if self_correction_applied else 'on first attempt'})"
            )
        else:
            logger.warning(
                f"⚠️ Self-correction loop failed after {num_attempts} attempts"
            )

        # Step 4: Generate Explanation
        logger.info("💬 Generating explanation...")
        explainer_chain = get_explainer_chain()
        explanation = await asyncio.to_thread(
            explainer_chain.invoke,
            {"sql_query": final_sql}
        )
        logger.info("✅ Explanation complete")

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000

        # Determine validation status
        validation_status = ValidationStatus.SUCCESS if success else ValidationStatus.FAILED
        validation_message = (
            f"Query executed successfully{f' after {num_attempts} attempts' if self_correction_applied else ''}"
            if success
            else f"Query validation failed after {num_attempts} attempts. Last error: {correction_history[-1].error_message if correction_history else 'Unknown error'}"
        )

        logger.info(f"✨ Request completed in {execution_time:.2f}ms")

        # Format correction history for response
        correction_history_formatted = [
            {
                "attempt": att.attempt_number,
                "error": att.error_message,
                "success": att.success
            }
            for att in correction_history
        ] if correction_history else None

        return QueryResponse(
            natural_language_question=request.question,
            sql_query=final_sql,
            explanation=explanation,
            validation_status=validation_status,
            validation_message=validation_message,
            execution_time_ms=execution_time,
            plan=structured_plan if isinstance(structured_plan, dict) else None,
            # RAG metadata
            tables_retrieved=tables_retrieved if rag_enabled else None,
            rag_enabled=rag_enabled,
            # Self-correction metadata
            correction_attempts=num_attempts,
            self_correction_applied=self_correction_applied,
            correction_history=correction_history_formatted
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@app.post("/index-schema")
async def index_schema(schema: str):
    """
    Index a new database schema for RAG retrieval.
    
    Args:
        schema: SQL DDL schema to index
    """
    try:
        logger.info("Indexing new schema...")
        await asyncio.to_thread(initialize_schema_rag, schema)
        
        rag = get_schema_rag()
        table_count = len(rag.get_all_table_names())
        
        return {
            "status": "success",
            "message": f"Schema indexed successfully: {table_count} tables",
            "tables_indexed": table_count
        }
    except Exception as e:
        logger.error(f"Error indexing schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index schema: {str(e)}"
        )

@app.get("/rag-status")
async def get_rag_status():
    """Get status of the Schema-Aware RAG system."""
    rag = get_schema_rag()
    
    if not rag.schema_loaded:
        return {
            "status": "not_initialized",
            "message": "Schema RAG not initialized",
            "tables_indexed": 0
        }
    
    table_names = rag.get_all_table_names()
    
    return {
        "status": "initialized",
        "message": "Schema RAG ready",
        "tables_indexed": len(table_names),
        "tables": table_names
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    rag = get_schema_rag()
    
    return {
        "status": "healthy",
        "service": "QueryScribe AI v2.0",
        "features": {
            "schema_aware_rag": rag.schema_loaded,
            "self_correction_loop": True
        }
    }

@app.get("/llm-info")
async def get_llm_info():
    """Get information about the current LLM configuration."""
    from ..core.llm import get_llm_info
    return get_llm_info()

@app.get("/config")
async def get_config():
    """Get non-sensitive application configuration."""
    from ..core.config import settings
    return {
        "llm_provider": settings.llm_provider.value,
        "model": settings.get_model_name(),
        "temperature": settings.temperature,
        "max_retries": settings.max_retries,
        "request_timeout": settings.request_timeout,
        "cors_origins": settings.cors_origins,
        "features": {
            "schema_aware_rag": True,
            "self_correction_loop": True,
            "max_correction_attempts": 3
        }
    }
