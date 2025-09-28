from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from ..core.llm import get_llm

def get_generator_chain() -> Runnable[Dict[str, Any], str]:
    """
    Creates and returns the chain for the SQL Generation Agent.
    
    This agent takes the structured plan from the Analyzer Agent and
    constructs the final SQL query.
    """
    llm = get_llm()

    prompt_template = """
    You are an expert SQL writer. Your job is to write a clean, efficient, and executable
    SQL query based on a provided structured plan.

    **SQL Dialect:** PostgreSQL

    **Structured Plan:**
    ```json
    {plan}
    ```

    **Instructions:**
    - Generate a single, executable SQL query.
    - Do not add any explanations or comments outside of the SQL code.
    - Ensure the syntax is correct for the specified SQL dialect.
    """
    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    
    return prompt | llm | StrOutputParser()