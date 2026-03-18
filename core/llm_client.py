import os
from dataclasses import dataclass

import requests

LLM_ERROR_PREFIX = "LLM_ERROR:"


class LLMError(RuntimeError):
    pass


@dataclass
class LLMRequest:
    prompt: str
    model: str
    temperature: float = 0.4


class BaseLLMClient:
    def complete(self, request: LLMRequest) -> str:
        raise NotImplementedError


class GroqLLMClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1/chat/completions",
        timeout: int = 120,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.base_url = base_url
        self.timeout = timeout

    def complete(self, request: LLMRequest) -> str:
        if not self.api_key:
            raise LLMError("GROQ_API_KEY not found in environment.")

        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LLMError(f"Groq request failed: {exc}") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Groq response did not include a message payload.") from exc


DEFAULT_MODEL_NAME = "llama-3.3-70b-versatile"


def get_default_client() -> BaseLLMClient:
    provider = os.environ.get("NEGOTIATION_LLM_PROVIDER", "groq").lower()
    if provider != "groq":
        raise LLMError(f"Unsupported LLM provider: {provider}")
    return GroqLLMClient()


def ask_llm(prompt: str, model: str = DEFAULT_MODEL_NAME, client: BaseLLMClient | None = None) -> str:
    active_client = client or get_default_client()
    return active_client.complete(LLMRequest(prompt=prompt, model=model))


def is_llm_error(text: str) -> bool:
    return str(text).startswith(LLM_ERROR_PREFIX)


def format_llm_error_message(message: str) -> str:
    return f"{LLM_ERROR_PREFIX} {message}"
