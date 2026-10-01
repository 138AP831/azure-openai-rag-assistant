import os

from langchain_openai import AzureChatOpenAI


def build_chat_model() -> AzureChatOpenAI:
    required = (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
    )
    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise ValueError(
            "Missing environment variables: " + ", ".join(missing)
        )

    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        temperature=0,
    )
