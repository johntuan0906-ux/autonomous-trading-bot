from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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


class ConsensusTurn(StrictModel):
    content: str
    recommendation: str
    agrees_with_all: bool
    open_disagreements: list[str]

    @field_validator("content", "recommendation")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Agent tra ve noi dung rong")
        return value

    @model_validator(mode="after")
    def consistent_agreement(self) -> "ConsensusTurn":
        if self.agrees_with_all and self.open_disagreements:
            raise ValueError("agrees_with_all=true nhung van con open_disagreements")
        return self
