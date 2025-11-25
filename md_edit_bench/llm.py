"""LLM client with usage tracking for OpenRouter."""

from __future__ import annotations

from collections.abc import Iterable
from typing import overload

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from md_edit_bench import config
from md_edit_bench.models import LLMCall, LLMUsage


@overload
async def call_llm(
    model: str,
    messages: str,
    system: str | None = None,
    response_format: type[BaseModel] | None = None,
) -> tuple[str, LLMUsage]: ...


@overload
async def call_llm(
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    system: str | None = None,
    response_format: type[BaseModel] | None = None,
) -> tuple[str, LLMUsage]: ...


async def call_llm(
    model: str,
    messages: Iterable[ChatCompletionMessageParam] | str,
    system: str | None = None,
    response_format: type[BaseModel] | None = None,
) -> tuple[str, LLMUsage]:
    """Make an async LLM completion request and return content + usage.

    Args:
        model: Model ID (e.g., "openai/gpt-4o")
        messages: User message string or list of chat messages
        system: Optional system prompt (prepended to messages)
        response_format: Optional Pydantic model class for structured output (JSON mode)
    """
    full_messages: list[ChatCompletionMessageParam] = []
    if system:
        full_messages.append({"role": "system", "content": system})

    if isinstance(messages, str):
        full_messages.append({"role": "user", "content": messages})
    else:
        full_messages.extend(messages)

    if not config.API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set. Please set it to run benchmarks."
        )

    client = AsyncOpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)

    if response_format is not None:
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=full_messages,
            response_format=response_format,
            extra_body={"usage": {"include": True}},
            timeout=60 * 10,
        )
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            extra_body={"usage": {"include": True}},
            timeout=60 * 10,
        )
    content = response.choices[0].message.content or ""

    # Build request string for logging
    request_parts: list[str] = []
    for msg in full_messages:
        role = msg.get("role", "unknown")
        msg_content = msg.get("content", "")
        request_parts.append(f"[{role}]\n{msg_content}")
    request_str = "\n\n".join(request_parts)

    usage = LLMUsage(calls=[LLMCall(model=model, request=request_str, response=content)])
    if response.usage:
        usage.tokens_in = response.usage.prompt_tokens or 0
        usage.tokens_out = response.usage.completion_tokens or 0

        # OpenRouter-specific cost extraction from model_extra (untyped extension)
        if hasattr(response, "model_extra") and response.model_extra:
            extra: object = response.model_extra  # pyright: ignore[reportUnknownMemberType]
            if isinstance(extra, dict) and "usage" in extra:  # pyright: ignore[reportUnnecessaryIsInstance]
                usage_data: object = extra["usage"]  # pyright: ignore[reportAny]
                if isinstance(usage_data, dict) and "total_cost" in usage_data:
                    cost_val: object = usage_data["total_cost"]  # pyright: ignore[reportUnknownVariableType]
                    if isinstance(cost_val, int | float):
                        usage.cost_usd = float(cost_val)

        # Fallback to usage.cost if available (OpenRouter extension)
        if usage.cost_usd == 0.0 and hasattr(response.usage, "cost"):
            cost_attr = getattr(response.usage, "cost", None)  # pyright: ignore[reportAny]
            if isinstance(cost_attr, int | float):
                usage.cost_usd = float(cost_attr)

    return content, usage
