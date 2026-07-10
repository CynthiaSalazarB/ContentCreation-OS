from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunContext:
    """Execution context the orchestrator hands to every module's run().

    All fields are optional overrides; modules fall back to core.paths defaults.
    """

    dry_run: bool = False
    verbose: bool = False
    db_path: Path | None = None
    data_dir: Path | None = None
    config_path: Path | None = None


@dataclass
class RunResult:
    """Uniform summary every module's run() returns to the orchestrator."""

    module: str
    ok: bool = True
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    duration_s: float = 0.0

    def summary(self) -> str:
        status = "ok" if self.ok else "FAILED"
        parts = " ".join(f"{key}={value}" for key, value in self.counts.items())
        line = f"[{self.module}] {status}"
        if parts:
            line += f" {parts}"
        if self.errors:
            line += f" errors={len(self.errors)}"
        return f"{line} ({self.duration_s:.1f}s)"
