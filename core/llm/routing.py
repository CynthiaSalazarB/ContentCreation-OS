from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from core.paths import CONFIG_DIR


@dataclass
class TaskConfig:
    provider: str
    model: str
    max_output_tokens: int = 1024
    temperature: float = 0.5


@dataclass
class LlmRouting:
    default_provider: str
    providers: dict[str, dict[str, Any]]
    tasks: dict[str, TaskConfig]

    def task(self, name: str) -> TaskConfig:
        if name not in self.tasks:
            raise KeyError(f"Unknown LLM task: {name}")
        return self.tasks[name]


def load_llm_routing(path: Path | None = None) -> LlmRouting:
    config_path = path or (CONFIG_DIR / "llm_routing.yaml")
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    tasks = {
        name: TaskConfig(
            provider=cfg.get("provider", raw.get("default_provider", "gemini")),
            model=cfg["model"],
            max_output_tokens=int(cfg.get("max_output_tokens", 1024)),
            temperature=float(cfg.get("temperature", 0.5)),
        )
        for name, cfg in raw.get("tasks", {}).items()
    }
    return LlmRouting(
        default_provider=str(raw.get("default_provider", "gemini")),
        providers=dict(raw.get("providers", {})),
        tasks=tasks,
    )
