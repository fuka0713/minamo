"""設定（すべて環境変数から読む）。秘密の値はコードに書かない。"""

import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://")

# 画像の保存先（S3 と同じ使い方ができるストレージ。compose では SeaweedFS）
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "app")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "app")
S3_BUCKET = os.environ.get("S3_BUCKET", "screenshots")

# AI 解析（任意）。GEMINI_API_KEY を入れたときだけ Gemini を使う。入れなければ OCR とルールで解析する
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# 日付の計算に使うタイムゾーン（リマインドの「夜20時」などはこの時刻）
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Tokyo")

# CSRF 対策の追加の確認（任意）。カンマ区切りで書くと、書き込み系の API で Origin を確かめる
TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("TRUSTED_ORIGINS", "").split(",") if o.strip()]

# ログインのクッキー
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30日
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"  # https で公開するときは true

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 1枚 10MB まで
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
# たくさん送りすぎないように：1人あたり、10分間に登録できるスクショの数（フォルダごとの追加も、これを超えると 429）
UPLOAD_LIMIT_PER_10MIN = int(os.environ.get("UPLOAD_LIMIT_PER_10MIN", "40"))

# デモ：メールアドレスとパスワードなしで入れる「ゲスト」を許すか（本番で閉じるときは false）
ALLOW_GUEST = os.environ.get("ALLOW_GUEST", "true").lower() == "true"
# デモ：みんなで使う「ユーザー名 test / パスワード test」のアカウント（ALLOW_GUEST が true のときだけ）
DEMO_USERNAME = "test"
DEMO_PASSWORD = "test"
DEMO_EMAIL = "test@demo.invalid"
