"""生活スタイル（5問の診断）の入出力。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Question(BaseModel):
    id: str = Field(examples=["payday"])
    text: str = Field(examples=["お給料日はいつごろ？"])
    choices: list[str]
    multiple: bool = Field(False, description="（追加）複数選べる質問か")


class QuestionList(BaseModel):
    questions: list[Question] = Field(min_length=5, max_length=5)


class Answer(BaseModel):
    questionId: str
    value: str = Field(description="選んだ答え。複数選べる質問は「、」でつなぐ（例：コスメ、暮らし）")


class DiagnosisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[Answer] = Field(min_length=5, max_length=5, description="5問すべての答え")


class LifestyleOut(BaseModel):
    payday: int = Field(ge=1, le=31, description="給料日")
    source: Literal["default", "diagnosed", "manual"] = Field(description="default=まだ診断していない（仮の値） / diagnosed=診断の回答 / manual=あとから変更")
    preferences: dict = Field(default_factory=dict, description="favoriteGenres・shoppingStyle・budgetTiming・reminderTime など")


class LifestylePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payday: int | None = Field(None, ge=1, le=31)
    preferences: dict | None = None
