from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable
from ..core.llm import get_llm

def get_analyzer_chain() -> Runnable[Dict[str, Any], Dict[str, Any]]:
    """
    Creates and returns the chain for the Schema & Intent Analyzer agent.
    
    This agent's job is to understand the database schema and the user's question,
    then output a structured JSON plan for the next agent.
    """
    llm = get_llm()

    # This prompt template is crucial. It guides the LLM to deconstruct the user's
    # question based on the provided database schema.
    prompt_template = """
    You are an expert at analyzing database schemas and user questions.
    Your goal is to create a structured plan in JSON format to generate a SQL query.

    Analyze the user's question and the database schema provided below.

    **Database Schema:**
    ```sql
    {schema}
    ```

    **User's Question:**
    "{user_question}"

    **Instructions:**
    Based on the schema and question, identify the necessary tables, columns, join conditions,
    filters, and any aggregations or orderings required.
    
    Output a JSON object containing the plan. The JSON should have keys like 
    'tables', 'columns', 'joins', 'filters', 'group_by', 'order_by', 'limit'.
    
    {format_instructions}
    """
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_template(template=prompt_template, partial_variables={"format_instructions": parser.get_format_instructions()})
    
    return prompt | llm | parser