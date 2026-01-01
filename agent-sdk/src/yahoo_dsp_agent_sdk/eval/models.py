import boto3
from botocore.config import Config
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_aws import ChatBedrock

from .constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_REGION,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_CONNECT,
    DEFAULT_TIMEOUT_READ,
)


class AWSBedrockEvalModel(DeepEvalBaseLLM):
    def __init__(self, model):
        self.model = model

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        return chat_model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        res = await chat_model.ainvoke(prompt)
        return res.content

    def get_model_name(self):
        return self.model.model_id


def create_bedrock_eval_model(
    model_id: str = DEFAULT_MODEL_ID,
    region: str = DEFAULT_REGION,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    timeout_connect: int = DEFAULT_TIMEOUT_CONNECT,
    timeout_read: int = DEFAULT_TIMEOUT_READ,
    retry_max_attempts: int = DEFAULT_RETRY_MAX_ATTEMPTS,
) -> AWSBedrockEvalModel:
    config = Config(
        connect_timeout=timeout_connect,
        read_timeout=timeout_read,
        retries={"max_attempts": retry_max_attempts, "mode": "adaptive"},
    )
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
        config=config,
    )
    chat_model = ChatBedrock(
        model_id=model_id,
        client=bedrock_client,
        model_kwargs={"max_tokens": max_tokens, "temperature": temperature},
        region_name=region,
    )
    return AWSBedrockEvalModel(model=chat_model)
