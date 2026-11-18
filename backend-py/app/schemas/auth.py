"""アカウントの入出力。"""

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str = Field(description="メールアドレス", examples=["hello@example.com"])
    password: str = Field(description="パスワード（登録のときは8文字以上）", examples=["password1"])


class UserOut(BaseModel):
    id: str = Field(examples=["usr_1a2b3c"])
    email: str = Field(examples=["hello@example.com"])
