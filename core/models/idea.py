from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from core.models.news_item import Source

IdeaProcessingStatus = Literal[
    "captured",
    "filtered",
    "scored",
    "angled",
    "synced",
    "published",
]
BrandLane = Literal["build", "create", "reflect"]
HumanDecision = Literal["approved", "rejected", "edit_requested", "pending"]
ContentIntent = Literal["educational", "opinion", "tutorial", "story"]
DeliveryFormat = Literal["talking head", "silent film", "carousel", "voiceover"]
HookFamily = Literal["promise", "moment"]
ContentStage = Literal["reach", "trust", "proof", "resonance"]


class IdeaContent(BaseModel):
    raw_text: str
    title: str | None = None
    context: str | None = None
    tags: list[str] = Field(default_factory=list)


class IdeaClassification(BaseModel):
    topic: str | None = None
    intent: ContentIntent | None = None
    audience_fit: float | None = Field(default=None, ge=0.0, le=1.0)
    noise_score: float | None = Field(default=None, ge=0.0, le=1.0)


class BrandFit(BaseModel):
    """Advisory brand alignment score — never blocks the pipeline."""

    fit: float | None = Field(default=None, ge=0.0, le=1.0)
    note: str | None = None
    lane: BrandLane | None = None


class ScriptAngle(BaseModel):
    """One suggested angle. All suggestion fields are advisory — the human picks."""

    framework: str
    hook: str
    angle: str
    tone: str | None = None
    estimated_length: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    # Added 2026-08-13. Optional so pre-existing ideas still validate — no backfill needed.
    delivery_format: DeliveryFormat | None = None
    hook_family: HookFamily | None = None
    hook_mechanism: str | None = None
    stage: ContentStage | None = None


class IdeaLinks(BaseModel):
    related_news_ids: list[str] = Field(default_factory=list)
    related_idea_ids: list[str] = Field(default_factory=list)
    market_insight_ids: list[str] = Field(default_factory=list)


class IdeaProcessing(BaseModel):
    status: IdeaProcessingStatus = "captured"
    pipeline_version: str = "2b"
    agent_runs: list[dict] = Field(default_factory=list)


class IdeaHuman(BaseModel):
    decision: HumanDecision = "pending"
    selected_angle_index: int | None = None
    final_script: str | None = None
    notes: str | None = None
    decided_at: datetime | None = None


class IdeaSync(BaseModel):
    notion_page_id: str | None = None
    last_synced_at: datetime | None = None


class Idea(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["idea"] = "idea"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Source = Field(
        default_factory=lambda: Source(type="manual", name="cli_capture", url=None)
    )
    content: IdeaContent
    classification: IdeaClassification = Field(default_factory=IdeaClassification)
    brand_fit: BrandFit = Field(default_factory=BrandFit)
    script_angles: list[ScriptAngle] = Field(default_factory=list)
    links: IdeaLinks = Field(default_factory=IdeaLinks)
    processing: IdeaProcessing = Field(default_factory=IdeaProcessing)
    human: IdeaHuman = Field(default_factory=IdeaHuman)
    sync: IdeaSync = Field(default_factory=IdeaSync)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
