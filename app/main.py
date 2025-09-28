import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import QueryRequest, QueryResponse, ErrorResponse
from ..agents.analyzer_agent import get_analyzer_chain
from ..agents.generator_agent import get_generator_chain
from ..agents.explainer_agent import get_explainer_chain
from ..db.validator import validate_sql_query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QueryScribe AI",
    description="An API for converting natural language questions into SQL queries with explanations.",
    version="1.0.0",
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

async def run_agents_concurrently(schema: str, question: str, plan: Dict[str, Any]) -> tuple:
    """Run SQL generation and explanation agents concurrently."""
    async def run_generator():
        generator_chain = get_generator_chain()
        return generator_chain.invoke({"plan": plan})

    # For now, keep explanation sequential since it depends on SQL
    # In future iterations, we could potentially run validation in parallel
    sql_query = await asyncio.to_thread(run_generator)

    async def run_explainer():
        explainer_chain = get_explainer_chain()
        return explainer_chain.invoke({"sql_query": sql_query})

    async def run_validator():
        return validate_sql_query(sql_query)

    # Run explanation and validation in parallel
    explanation, (is_valid, validation_message) = await asyncio.gather(
        asyncio.to_thread(run_explainer),
        asyncio.to_thread(run_validator)
    )

    return sql_query, explanation, is_valid, validation_message

@app.post("/generate-sql", response_model=QueryResponse)
async def generate_sql(request: QueryRequest):
    """
    The main endpoint that orchestrates the multi-agent pipeline.
    Processes natural language questions and converts them to SQL queries.
    """
    import time
    start_time = time.time()

    logger.info(f"Processing question: {request.question[:100]}...")

    # Load schema if not provided
    db_schema = request.db_schema
    if not db_schema:
        db_schema = await load_schema()

    try:
        # Agent 1: Schema & Intent Analyzer
        logger.info("Running schema and intent analysis...")
        analyzer_chain = get_analyzer_chain()
        structured_plan = await asyncio.to_thread(
            analyzer_chain.invoke,
            {"schema": db_schema, "user_question": request.question}
        )
        logger.info("Analysis complete")

        # Agents 2 & 3: SQL Generation and Explanation (with validation)
        logger.info("Generating SQL and explanation...")
        sql_query, explanation, is_valid, validation_message = await run_agents_concurrently(
            db_schema, request.question, structured_plan
        )
        logger.info("SQL generation and explanation complete")

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000

        validation_status = ValidationStatus.SUCCESS if is_valid else ValidationStatus.FAILED
        logger.info(f"Request completed in {execution_time:.2f}ms - Validation: {validation_status}")

        return QueryResponse(
            natural_language_question=request.question,
            sql_query=sql_query,
            explanation=explanation,
            validation_status=validation_status,
            validation_message=validation_message,
            execution_time_ms=execution_time,
            plan=structured_plan if isinstance(structured_plan, dict) else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "QueryScribe AI"}

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
    }