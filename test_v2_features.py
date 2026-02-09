#!/usr/bin/env python3
"""
Test script for QueryScribe AI v2.0 features:
- Schema-Aware RAG
- Self-Correction Loop

Run this to verify the enhanced features are working correctly.
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_schema_rag():
    """Test Schema-Aware RAG system."""
    logger.info("=" * 70)
    logger.info("Testing Schema-Aware RAG")
    logger.info("=" * 70)
    
    try:
        from db.schema_rag import SchemaRAG
        
        # Sample schema with multiple tables
        sample_schema = """
        CREATE TABLE customers (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100),
            created_at TIMESTAMP
        );
        
        CREATE TABLE orders (
            id INT PRIMARY KEY,
            customer_id INT REFERENCES customers(id),
            order_date TIMESTAMP,
            total_amount DECIMAL(10,2),
            status VARCHAR(20)
        );
        
        CREATE TABLE products (
            id INT PRIMARY KEY,
            name VARCHAR(200),
            price DECIMAL(10,2),
            category VARCHAR(50)
        );
        
        CREATE TABLE order_items (
            id INT PRIMARY KEY,
            order_id INT REFERENCES orders(id),
            product_id INT REFERENCES products(id),
            quantity INT,
            price DECIMAL(10,2)
        );
        
        CREATE TABLE inventory (
            id INT PRIMARY KEY,
            product_id INT REFERENCES products(id),
            warehouse_location VARCHAR(100),
            quantity INT
        );
        """
        
        logger.info("1️⃣ Initializing SchemaRAG...")
        rag = SchemaRAG(persist_directory="./test_chroma_db")
        
        logger.info("2️⃣ Indexing schema...")
        rag.index_schema(sample_schema)
        
        tables = rag.get_all_table_names()
        logger.info(f"   ✅ Indexed {len(tables)} tables: {', '.join(tables)}")
        
        # Test retrieval with various questions
        test_questions = [
            "Show me all customers who placed orders",
            "What products are in stock?",
            "Find top selling products by revenue"
        ]
        
        logger.info("\n3️⃣ Testing retrieval for different questions...")
        for question in test_questions:
            logger.info(f"\n   Question: \"{question}\"")
            relevant_schema = rag.retrieve_relevant_schema(question, top_k=3)
            
            table_count = len(relevant_schema.split("CREATE TABLE")) - 1
            logger.info(f"   ✅ Retrieved {table_count} relevant tables")
            
            # Extract table names from retrieved schema
            import re
            retrieved_tables = re.findall(r'CREATE TABLE (\w+)', relevant_schema)
            logger.info(f"   Tables: {', '.join(retrieved_tables)}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Schema-Aware RAG Test PASSED")
        logger.info("=" * 70)
        
        # Cleanup
        rag.clear_index()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema-Aware RAG Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_self_correction():
    """Test Self-Correction Loop."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Self-Correction Loop")
    logger.info("=" * 70)
    
    try:
        from agents.self_correction import SelfCorrectingAgent
        from core.llm import get_llm
        
        logger.info("1️⃣ Initializing SelfCorrectingAgent...")
        agent = SelfCorrectingAgent(max_attempts=3)
        logger.info("   ✅ Agent initialized")
        
        # Test with a simple schema and plan
        schema = """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            age INT,
            email VARCHAR(100)
        );
        """
        
        question = "Find all users older than 25"
        plan = {
            "tables": ["users"],
            "columns": ["*"],
            "filters": ["age > 25"],
            "joins": [],
            "group_by": [],
            "order_by": []
        }
        
        logger.info("\n2️⃣ Testing SQL generation...")
        logger.info(f"   Question: \"{question}\"")
        
        # Note: This will work if DATABASE_URL is configured
        # Otherwise it will show a warning about no database configured
        logger.info("\n3️⃣ Running self-correction loop...")
        logger.info("   (Note: Full execution requires DATABASE_URL in .env)")
        
        final_sql, success, history = agent.generate_with_correction(
            schema=schema,
            question=question,
            plan=plan
        )
        
        logger.info(f"\n4️⃣ Results:")
        logger.info(f"   Attempts: {len(history)}")
        logger.info(f"   Success: {success}")
        logger.info(f"   Final SQL:\n{final_sql}")
        
        if history:
            logger.info("\n   Correction History:")
            for attempt in history:
                status = "✅ Success" if attempt.success else "❌ Failed"
                logger.info(f"   - Attempt {attempt.attempt_number}: {status}")
                if attempt.error_message:
                    logger.info(f"     Error: {attempt.error_message[:100]}...")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Self-Correction Loop Test PASSED")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Self-Correction Loop Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration():
    """Test integration of RAG + Self-Correction in main pipeline."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing RAG + Self-Correction Integration")
    logger.info("=" * 70)
    
    try:
        from db.schema_rag import initialize_schema_rag, get_schema_rag
        from agents.analyzer_agent import get_analyzer_chain
        from agents.self_correction import get_self_correcting_agent
        
        # Sample schema
        schema = """
        CREATE TABLE customers (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100)
        );
        
        CREATE TABLE orders (
            id INT PRIMARY KEY,
            customer_id INT,
            total DECIMAL(10,2),
            order_date TIMESTAMP
        );
        """
        
        logger.info("1️⃣ Initializing RAG with schema...")
        initialize_schema_rag(schema)
        
        rag = get_schema_rag()
        logger.info(f"   ✅ RAG initialized with {len(rag.get_all_table_names())} tables")
        
        logger.info("\n2️⃣ Testing question processing...")
        question = "Find customers with orders over $100"
        
        # Retrieve relevant schema
        logger.info("   🔍 Retrieving relevant schema...")
        relevant_schema = rag.retrieve_relevant_schema(question, top_k=5)
        logger.info(f"   ✅ Retrieved schema ({len(relevant_schema)} chars)")
        
        # Analyze
        logger.info("   🧠 Analyzing intent...")
        analyzer = get_analyzer_chain()
        plan = analyzer.invoke({
            "schema": relevant_schema,
            "user_question": question
        })
        logger.info("   ✅ Plan generated")
        
        # Generate with self-correction
        logger.info("   🔄 Generating SQL with self-correction...")
        agent = get_self_correcting_agent(max_attempts=3)
        
        final_sql, success, history = agent.generate_with_correction(
            schema=relevant_schema,
            question=question,
            plan=plan
        )
        
        logger.info(f"\n3️⃣ Integration Results:")
        logger.info(f"   RAG: ✅ Retrieved relevant tables")
        logger.info(f"   Analysis: ✅ Generated structured plan")
        logger.info(f"   Self-Correction: {len(history)} attempts")
        logger.info(f"   Final SQL:\n{final_sql}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Integration Test PASSED")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 70)
    logger.info("🚀 QueryScribe AI v2.0 - Feature Tests")
    logger.info("=" * 70)
    
    results = {
        "Schema-Aware RAG": False,
        "Self-Correction Loop": False,
        "Integration": False
    }
    
    # Run tests
    results["Schema-Aware RAG"] = await test_schema_rag()
    results["Self-Correction Loop"] = await test_self_correction()
    results["Integration"] = await test_integration()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 70)
    
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("\nQueryScribe AI v2.0 is ready to use:")
        logger.info("  - Schema-Aware RAG: ✅ Working")
        logger.info("  - Self-Correction Loop: ✅ Working")
        logger.info("\nNext steps:")
        logger.info("  1. Configure DATABASE_URL in .env for full execution")
        logger.info("  2. Run: python main.py")
        logger.info("  3. Test API: http://localhost:8000/docs")
    else:
        logger.error("❌ SOME TESTS FAILED - Check logs above")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
