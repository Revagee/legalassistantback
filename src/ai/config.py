from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.language_models import BaseChatModel

config = {
    "embeddings": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
    },
    "chat_name": {
        "provider": "google",
        "model": "gemini-2.5-flash-lite",
        "max_tokens": 30,
        "max_retries": 2,
    },
    "chat": {
        "provider": "google",
        "model": "gemini-2.5-pro",
        "max_retries": 2,
    },
    "query_generation": {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "max_retries": 2,
    },
}


@lru_cache(maxsize=5)
def get_llm(purpose: str) -> BaseChatModel:
    model_config = config[purpose]
    provider = model_config["provider"]

    providers = {
        "openai": ChatOpenAI,
        "anthropic": ChatAnthropic,
        "google": ChatGoogleGenerativeAI,
    }

    if provider not in providers:
        raise ValueError(f"Invalid provider: {provider}")

    llm_class = providers[provider]
    params = {
        "model": model_config["model"],
        "max_tokens": model_config.get("max_tokens", None),
        "max_retries": model_config.get("max_retries", 2),
    }

    return llm_class(**params)


@lru_cache(maxsize=1)
def get_embeddings_model():
    model_config = config["embeddings"]
    if model_config["provider"] == "openai":
        return OpenAIEmbeddings(
            model=model_config["model"],
            dimensions=model_config["dimensions"],
        )
    else:
        raise ValueError(f"Invalid provider: {model_config['provider']}")
