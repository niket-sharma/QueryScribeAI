#!/usr/bin/env python3
"""
QueryScribeAI - A multi-agent system for converting natural language to SQL queries.

This is the main entry point for running the application.

Version 2.0:
- Schema-Aware RAG for intelligent schema retrieval
- Self-Correction Loop for iterative query fixing
"""

import logging
import uvicorn
from app.main_v2 import app  # Use enhanced version with RAG and self-correction
from core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, getattr(settings, 'log_level', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting QueryScribeAI v2.0...")
    logger.info(f"📡 LLM Provider: {settings.llm_provider.value}")
    logger.info("✨ Features: Schema-Aware RAG + Self-Correction Loop")

    uvicorn.run(
        "app.main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
