"""API schemas. Serialised with camelCase aliases to match the frontend types."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


DocumentStatus = Literal["uploaded", "processing", "ready", "failed"]
StepStatus = Literal["pending", "running", "done", "failed"]


class ProcessingStep(CamelModel):
    key: str
    label: str
    status: StepStatus = "pending"
    percent: int | None = None


class DocumentOut(CamelModel):
    id: str
    title: str
    authors: list[str]
    affiliations: list[str]
    abstract: str | None = None
    keywords: list[str]
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    file_name: str
    file_size: int
    page_count: int
    status: DocumentStatus
    steps: list[ProcessingStep]
    error: str | None = None
    created_at: datetime


class DocumentPatch(CamelModel):
    title: str | None = None
    authors: list[str] | None = None
    affiliations: list[str] | None = None
    abstract: str | None = None
    keywords: list[str] | None = None
    year: int | None = None
    doi: str | None = None
    venue: str | None = None


class SectionOut(CamelModel):
    id: str
    document_id: str
    title: str
    section_number: str | None = None
    kind: str
    order: int
    start_page: int
    end_page: int | None = None


class BoundingBox(CamelModel):
    x: float
    y: float
    width: float
    height: float


class ParagraphOut(CamelModel):
    id: str
    document_id: str
    section_id: str
    page_number: int
    original_text: str
    translated_text: str | None = None
    order: int
    kind: str
    bounding_box: BoundingBox | None = None


class FigureOut(CamelModel):
    id: str
    document_id: str
    section_id: str | None = None
    page_number: int
    caption: str
    label: str | None = None
    image_url: str


class TableOut(CamelModel):
    id: str
    document_id: str
    section_id: str | None = None
    page_number: int
    caption: str
    label: str | None = None
    rows: list[list[str]]


class Citation(CamelModel):
    page: int
    section: str
    paragraph_id: str
    snippet: str | None = None


ContextMode = Literal["entire_document", "current_section", "current_page", "selected_text"]
ExplanationLevel = Literal["beginner", "undergraduate", "graduate", "researcher"]
ChatAction = Literal["ask", "explain", "translate", "summarize"]


class ChatRequest(CamelModel):
    message: str = Field(min_length=1, max_length=8000)
    context: ContextMode = "entire_document"
    section_id: str | None = None
    page: int | None = None
    selected_text: str | None = None
    level: ExplanationLevel = "graduate"
    action: ChatAction = "ask"
    session_id: str | None = None


class ChatResponse(CamelModel):
    answer: str
    citations: list[Citation]
    session_id: str
    message_id: str


class ChatMessageOut(CamelModel):
    id: str
    role: str
    content: str
    citations: list[Citation] = []
    created_at: datetime


class ChatSessionOut(CamelModel):
    id: str
    document_id: str
    title: str
    created_at: datetime


class SearchRequest(CamelModel):
    query: str = Field(min_length=1, max_length=1000)
    type: Literal["exact", "semantic"] = "exact"
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(CamelModel):
    paragraph_id: str
    section_id: str
    section_title: str
    page: int
    preview: str
    score: float | None = None


class NoteCreate(CamelModel):
    paragraph_id: str
    content: str = Field(min_length=1)
    selected_text: str | None = None


class NoteOut(CamelModel):
    id: str
    document_id: str
    paragraph_id: str
    selected_text: str | None = None
    content: str
    created_at: datetime


class HighlightCreate(CamelModel):
    paragraph_id: str
    selected_text: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    color: str | None = None


class HighlightOut(CamelModel):
    id: str
    document_id: str
    paragraph_id: str
    selected_text: str
    start_offset: int
    end_offset: int
    color: str | None = None
    created_at: datetime


SummaryLength = Literal["one_sentence", "short", "detailed"]


class SummaryOut(CamelModel):
    document_id: str
    length: SummaryLength
    content: str
    citations: list[Citation]
    created_at: datetime


class TerminologyOut(CamelModel):
    term: str
    translation: str
    user_override: bool = False
