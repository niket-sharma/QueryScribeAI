from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from ..core.llm import get_llm

def get_explainer_chain() -> Runnable[Dict[str, Any], str]:
    """
    Creates and returns the chain for the Explanation Agent.
    
    This agent takes a SQL query and explains it in plain, non-technical
    language for a business user.
    """
    llm = get_llm()

    prompt_template = """
    You are an expert at explaining complex SQL queries to non-technical business managers.

    **SQL Query:**
    ```sql
    {sql_query}
    ```

    **Instructions:**
    Explain this SQL query step-by-step, breaking it down by clause (e.g., SELECT, FROM, WHERE).
    Use simple business terms and avoid technical jargon.
    """
    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    
    return prompt | llm | StrOutputParser()