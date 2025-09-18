from langchain.tools import StructuredTool
from typing import Literal, TypeAlias
from pydantic import BaseModel
from src.ai.config import get_llm
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_postgres import PGVector
from src.ai.config import get_embeddings_model
from functools import lru_cache
import os


SearchType: TypeAlias = Literal["constitution"] #, "laws", "codes", "judicial practice", "all"]


@lru_cache(maxsize=1) # TODO: increase when we have more collections
def get_vector_store(search_source: SearchType) -> PGVector:
    return PGVector(
        embeddings=get_embeddings_model(),
        collection_name=search_source,
        connection=os.getenv("POSTGRES_CONNECTION_STRING"),
        use_jsonb=True,
    )


class QueryGenerationOutput(BaseModel):
    queries: list[str]


def get_retriever(collection_name: SearchType):
    llm = get_llm("query_generation")
    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template="""You are an AI language model assistant. Your task is to generate five
        different versions of the given user question to retrieve relevant documents from a vector
        database. By generating multiple perspectives on the user question, your goal is to help
        the user overcome some of the limitations of the distance-based similarity search.
        Provide these alternative questions separated by newlines.
        Original question: {question}""",
    )
    llm_chain = QUERY_PROMPT | llm.with_structured_output(QueryGenerationOutput) | RunnableLambda(lambda x: x.queries)
    retriever = get_vector_store(collection_name)
    return MultiQueryRetriever(
        retriever=retriever,
        llm_chain=llm_chain,
    )


class InputData(BaseModel):
    query: str
    search_source: SearchType


async def search_documents(query: str, search_source: SearchType) -> str:
    retriever = get_retriever(search_source)

    docs = await retriever.ainvoke(query)

    return "\n\n".join([doc.page_content for doc in docs])


tool_description = """
Internal vector similarity search over Ukrainian legal texts.

When to use:
- Use to retrieve the exact text of legal norms for citations (e.g., Constitution of Ukraine articles), verify wording, or ground answers in primary sources.
- Prefer this over web search when the requested information is likely contained in our internal collections (currently: "constitution").
- Useful before drafting documents that require precise citations.

When not to use:
- Do not use for news, commentary, or content outside internal collections.
- If results are empty or insufficient, fall back to web search and state limitations.

How to call:
- Provide a concise Ukrainian query that describes the legal point or article needed.
""".strip()


tool = StructuredTool.from_function(
    name="similarity_search",
    description=tool_description,
    coroutine=search_documents,
    args_schema=InputData,
)
