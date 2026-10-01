from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

AgentName = Literal["planner", "builder", "reviewer"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(StrictModel):
    next_speaker: Literal["planner", "builder", "reviewer", "finish"]
    instruction: str


class Contribution(StrictModel):
    content: str
    next_agent: Literal["planner", "builder", "reviewer", "finish"]
    handoff_note: str

    @field_validator("content")
    @classmethod
    def nonempty_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Agent tra ve noi dung rong")
        return value


class FinalAnswer(StrictModel):
    answer_markdown: str
    limitations: list[str]

    @field_validator("answer_markdown")
    @classmethod
    def nonempty_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Ket qua tong hop rong")
        return value
