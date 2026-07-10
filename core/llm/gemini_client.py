from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from core.llm.routing import LlmRouting, TaskConfig, load_llm_routing
from core.paths import ENV_PATH


def _api_key_for_provider(routing: LlmRouting, provider: str) -> str:
    cfg = routing.providers.get(provider, {})
    for env_name in (
        cfg.get("api_key_env"),
        cfg.get("fallback_api_key_env"),
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        if not env_name:
            continue
        value = os.getenv(str(env_name), "").strip()
        if value:
            return value
    raise ValueError(
        f"No API key for provider '{provider}'. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env"
    )


def generate_json(
    task_name: str,
    *,
    system: str,
    user: str,
    routing: LlmRouting | None = None,
) -> dict[str, Any]:
    load_dotenv(ENV_PATH)
    routing = routing or load_llm_routing()
    task = routing.task(task_name)
    api_key = _api_key_for_provider(routing, task.provider)

    if task.provider != "gemini":
        raise ValueError(f"Unsupported provider: {task.provider}")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = f"{system.strip()}\n\n---\n\n{user.strip()}"
    config_kwargs: dict = {
        "response_mime_type": "application/json",
        "temperature": task.temperature,
        "max_output_tokens": task.max_output_tokens,
    }
    if task.model.startswith("gemini-2.5") or task.model.startswith("gemini-3"):
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    response = client.models.generate_content(
        model=task.model,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty response")
    return json.loads(text)


def task_config(task_name: str) -> TaskConfig:
    return load_llm_routing().task(task_name)
