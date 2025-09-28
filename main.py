#!/usr/bin/env python3
"""
QueryScribeAI - A multi-agent system for converting natural language to SQL queries.

This is the main entry point for running the application.
"""

import logging
import uvicorn
from app.main import app
from core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, getattr(settings, 'log_level', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting QueryScribeAI server...")
    logger.info(f"Using LLM provider: {settings.llm_provider.value}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )