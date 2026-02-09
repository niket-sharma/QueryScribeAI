"""
Schema-Aware RAG System for QueryScribe AI

This module implements a Retrieval-Augmented Generation (RAG) system for database schemas.
It uses vector embeddings to find relevant tables and columns based on semantic similarity
to the user's question, improving SQL generation accuracy for large schemas.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class SchemaRAG:
    """
    Schema-Aware RAG system for retrieving relevant database schema elements.
    
    This system:
    1. Parses SQL schema into individual table/column chunks
    2. Creates vector embeddings for semantic search
    3. Retrieves relevant schema parts based on user questions
    4. Returns focused schema context to improve SQL generation
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the Schema RAG system.
        
        Args:
            persist_directory: Directory to store Chroma vector database
        """
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",  # Fast, lightweight model
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectorstore: Optional[Chroma] = None
        self.schema_loaded = False
        
        logger.info(f"SchemaRAG initialized with persist directory: {persist_directory}")
    
    def parse_schema_to_chunks(self, schema_sql: str) -> List[Document]:
        """
        Parse SQL schema into semantic chunks (tables with their columns).
        
        Args:
            schema_sql: Full SQL schema as a string
            
        Returns:
            List of Document objects, each representing a table with metadata
        """
        documents = []
        
        # Split schema by CREATE TABLE statements
        table_pattern = r'CREATE TABLE\s+(\w+)\s*\((.*?)\);'
        tables = re.findall(table_pattern, schema_sql, re.DOTALL | re.IGNORECASE)
        
        for table_name, columns_def in tables:
            # Extract column information
            column_lines = [line.strip() for line in columns_def.split(',')]
            columns = []
            
            for line in column_lines:
                # Parse column definition (name, type, constraints)
                col_match = re.match(r'(\w+)\s+(\w+(?:\(\d+\))?)(.*)', line.strip())
                if col_match:
                    col_name, col_type, constraints = col_match.groups()
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'constraints': constraints.strip()
                    })
            
            # Create document for this table
            # Page content is human-readable description for semantic search
            page_content = f"Table: {table_name}\n"
            page_content += f"Columns: {', '.join([c['name'] for c in columns])}\n"
            page_content += "Column details:\n"
            
            for col in columns:
                page_content += f"  - {col['name']} ({col['type']})"
                if col['constraints']:
                    page_content += f" {col['constraints']}"
                page_content += "\n"
            
            # Metadata for filtering and reconstruction
            metadata = {
                'table_name': table_name,
                'column_count': len(columns),
                'columns': [c['name'] for c in columns],
                'full_definition': f"CREATE TABLE {table_name} ({columns_def});"
            }
            
            documents.append(Document(
                page_content=page_content,
                metadata=metadata
            ))
            
            logger.debug(f"Parsed table: {table_name} with {len(columns)} columns")
        
        logger.info(f"Parsed schema into {len(documents)} table chunks")
        return documents
    
    def index_schema(self, schema_sql: str):
        """
        Index a database schema for retrieval.
        
        Args:
            schema_sql: Full SQL schema as a string
        """
        logger.info("Indexing schema...")
        
        # Parse schema into chunks
        documents = self.parse_schema_to_chunks(schema_sql)
        
        if not documents:
            logger.warning("No tables found in schema")
            return
        
        # Create or update vector store
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        
        self.schema_loaded = True
        logger.info(f"Schema indexed successfully: {len(documents)} tables")
    
    def retrieve_relevant_schema(
        self, 
        question: str, 
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> str:
        """
        Retrieve relevant schema parts based on semantic similarity to the question.
        
        Args:
            question: User's natural language question
            top_k: Number of most relevant tables to retrieve
            score_threshold: Minimum similarity score (0-1)
            
        Returns:
            Focused SQL schema containing only relevant tables
        """
        if not self.schema_loaded or not self.vectorstore:
            logger.warning("Schema not indexed. Call index_schema() first.")
            return ""
        
        logger.info(f"Retrieving relevant schema for question: {question[:100]}...")
        
        # Retrieve relevant documents with scores
        results = self.vectorstore.similarity_search_with_score(
            question,
            k=top_k
        )
        
        # Filter by score threshold
        relevant_docs = [
            (doc, score) for doc, score in results 
            if score >= score_threshold
        ]
        
        if not relevant_docs:
            logger.warning("No relevant schema found above threshold")
            return ""
        
        # Build focused schema from relevant tables
        schema_parts = []
        for doc, score in relevant_docs:
            table_name = doc.metadata['table_name']
            full_def = doc.metadata['full_definition']
            schema_parts.append(full_def)
            
            logger.debug(
                f"Retrieved table '{table_name}' with similarity score: {score:.3f}"
            )
        
        focused_schema = "\n\n".join(schema_parts)
        
        logger.info(
            f"Retrieved {len(relevant_docs)} relevant tables out of {top_k} requested"
        )
        
        return focused_schema
    
    def get_all_table_names(self) -> List[str]:
        """
        Get list of all indexed table names.
        
        Returns:
            List of table names
        """
        if not self.schema_loaded or not self.vectorstore:
            return []
        
        # Get all documents
        all_docs = self.vectorstore.get()
        
        if not all_docs or 'metadatas' not in all_docs:
            return []
        
        table_names = [
            meta['table_name'] 
            for meta in all_docs['metadatas'] 
            if 'table_name' in meta
        ]
        
        return table_names
    
    def clear_index(self):
        """Clear the vector store index."""
        if self.vectorstore:
            self.vectorstore.delete_collection()
            self.vectorstore = None
            self.schema_loaded = False
            logger.info("Schema index cleared")


# Global instance
_schema_rag: Optional[SchemaRAG] = None


def get_schema_rag() -> SchemaRAG:
    """
    Get or create the global SchemaRAG instance.
    
    Returns:
        SchemaRAG instance
    """
    global _schema_rag
    if _schema_rag is None:
        _schema_rag = SchemaRAG()
    return _schema_rag


def initialize_schema_rag(schema_sql: str):
    """
    Initialize and index a schema in the global RAG instance.
    
    Args:
        schema_sql: SQL schema to index
    """
    rag = get_schema_rag()
    rag.index_schema(schema_sql)
    logger.info("Global SchemaRAG initialized and indexed")
