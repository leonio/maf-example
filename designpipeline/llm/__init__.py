"""Creates the chat client each agent runs on.

Every agent here is "a chat client + instructions + tools", so swapping OpenAI for Azure OpenAI, a local model
(Ollama, vLLM, LM Studio) or the offline script is a change in this one function. Nothing downstream knows.

OpenAI, Azure OpenAI's v1 endpoint and most local servers speak the same Chat Completions protocol, so one client
class with a different base URL covers them all. For Azure in production prefer keyless Entra ID auth
(`azure-identity`'s token provider passed to `AsyncOpenAI`) over an API key.

One client per agent (rather than one shared client) so each agent can use a different model
(`PIPELINE_MODEL_DEVELOPER=gpt-4.1`) and so the mock can script each agent separately.
"""

from __future__ import annotations

from ..config import Settings


def chat_client(settings: Settings, agent: str):
    if settings.is_mock:
        from .scripted import ScriptedChatClient

        return ScriptedChatClient(agent, delay=settings.mock_delay)

    from agent_framework_openai import OpenAIChatCompletionClient
    from openai import AsyncOpenAI

    if not settings.api_key and settings.provider != "openai-compatible":
        raise ValueError(f"PIPELINE_API_KEY (or OPENAI_API_KEY) is required for provider {settings.provider}.")
    return OpenAIChatCompletionClient(
        model=settings.model_for(agent),
        async_client=AsyncOpenAI(
            base_url=settings.endpoint_url(),
            # Ollama and many on-prem servers ignore the key, but the SDK insists on one.
            api_key=settings.api_key or "not-needed",
            max_retries=2,
        ),
    )
