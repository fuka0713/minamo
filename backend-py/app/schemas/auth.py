"""アカウントの入出力。デモなので、ユーザー名とパスワードだけの簡単なもの。"""

from pydantic import AliasChoices, BaseModel, Field


class Credentials(BaseModel):
    # 前の形（email）で送っても受けつける
    username: str = Field(validation_alias=AliasChoices("username", "email"), description="ユーザー名（すきな名前。メールアドレスでもよい）",
                          examples=["yuka"])
    password: str = Field(description="パスワード（登録のときは4文字以上）", examples=["pass"])


class UserOut(BaseModel):
    id: str = Field(examples=["usr_1a2b3c"])
    username: str = Field(description="ユーザー名", examples=["yuka"])
    email: str = Field(description="（前の形との互換のため。username と同じ値）", examples=["yuka"])
