"""生成 AI に頼む3つの仕事（どれも、失敗したら呼び出し元がルールに戻す）。

  1. extract_item     … スクショから商品の項目を取り出す（解析 API）
  2. recommend_dates  … いつ思い出させるとよいか（推薦日）と、その理由（推薦理由）を考える（推薦 API）
  3. nearby_reasons   … 近くにお店があるときの、通知の一言を考える（推薦 API）
"""

from datetime import date, datetime, time, timedelta

from app.services import llm
from app.services.genres import GENRES, genre_label
from app.services.timing import TZ

GENRE_IDS = [g["id"] for g in GENRES]
GENRE_GUIDE = "、".join(f'{g["id"]}={g["label"]}' for g in GENRES)
BASIS = ["period_end", "period_start", "deadline", "release_date", "payday", "weekend", "season", "place", "other"]


def _date(value) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _text(value, limit: int) -> str | None:
    return (value.strip()[:limit] or None) if isinstance(value, str) else None


# ---------------- 1. 解析：スクショから項目を取り出す ----------------

EXTRACT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "nullable": True},
        "description": {"type": "STRING", "nullable": True},
        "price": {"type": "INTEGER", "nullable": True},
        "genre": {"type": "STRING", "enum": GENRE_IDS},
        "storeName": {"type": "STRING", "nullable": True},
        "periodStart": {"type": "STRING", "nullable": True},
        "periodEnd": {"type": "STRING", "nullable": True},
        "deadline": {"type": "STRING", "nullable": True},
        "releaseDate": {"type": "STRING", "nullable": True},
    },
    "required": ["genre"],
}


def extract_item(image: bytes, today: date) -> dict:
    """画像から商品の項目を取り出す（analyzer.analyze と同じ形で返す）。"""
    prompt = f"""あなたは買い物メモの整理を手伝います。スクリーンショットに写っている「欲しいもの」を1つ読み取ってください。
- title：商品名（40文字以内）。分からなければ null
- description：どんなものかを日本語で1文（60文字以内）
- price：画像に書いてある価格（円・整数）。書いていなければ null（推測しない）
- genre：次の id のどれか → {GENRE_GUIDE}
- storeName：画像に書いてあるお店・ブランドの店舗名（例：IKEA、マツキヨ、アニメイト）。書いていなければ null
- periodStart / periodEnd：開催期間・販売期間の始まりと終わり、deadline：締切、releaseDate：発売日
  日付は YYYY-MM-DD。年が書いていなければ、今日（{today.isoformat()}）から見て近い未来の年にする。書いていなければ null"""
    data = llm.generate_json(prompt, EXTRACT_SCHEMA, image)
    price = data.get("price")
    return {
        "title": _text(data.get("title"), 40),
        "description": _text(data.get("description"), 60),
        "price": price if isinstance(price, int) and not isinstance(price, bool) and price > 0 else None,
        "genre": data["genre"] if data.get("genre") in GENRE_IDS else "other",
        "place_name": _text(data.get("storeName"), 100),
        "period_start": _date(data.get("periodStart")),
        "period_end": _date(data.get("periodEnd")),
        "deadline": _date(data.get("deadline")),
        "release_date": _date(data.get("releaseDate")),
    }


# ---------------- 2. 推薦：いつ思い出させるか ----------------

RECOMMEND_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "recommendations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "date": {"type": "STRING"},
                    "time": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                    "basis": {"type": "STRING", "enum": BASIS},
                },
                "required": ["date", "time", "reason", "basis"],
            },
        },
    },
    "required": ["recommendations"],
}


def recommend_dates(item: dict, context: dict, now: datetime) -> list[dict]:
    """推薦日と推薦理由を最大3つ考える。[{"remindAt", "reason", "basis"}]（早い順・未来だけ）。

    item：title・genre・price・期間など。context：給料日・ルールの候補・近くのお店（ダミーでもよい）。
    """
    today = now.astimezone(TZ).date()
    store = context.get("store")
    store_line = (f"{store['name']}（{store['area']}、{store['distanceM']}m 先）" if store and store.get("distanceM") is not None
                  else f"{store['name']}（{store['area']}）" if store else "わからない")
    hints = "\n".join(f"  - {h['remindAt'].astimezone(TZ):%Y-%m-%d %H:%M}：{h['reason']}" for h in context.get("hints", []))
    prompt = f"""あなたは、欲しいものを「ちょうどいいタイミング」で思い出させるアシスタントです。
次の欲しいものについて、いつ知らせるとよいか（推薦日）と、その理由（推薦理由）を最大3つ考えてください。

[欲しいもの]
- 商品名：{item.get("title") or "不明"}
- ジャンル：{genre_label(item.get("genre"))}
- 価格：{f"{item['price']}円" if item.get("price") else "不明"}
- 開催期間：{item.get("period_start") or "-"} 〜 {item.get("period_end") or "-"}
- 締切：{item.get("deadline") or "-"} ／ 発売日：{item.get("release_date") or "-"}
- 買えるお店：{store_line}

[知っていること]
- 今日：{today.isoformat()}（{"月火水木金土日"[today.weekday()]}曜日）
- 次の給料日：{context["payday"].isoformat()}
- 決まりごとで作った候補（参考）：
{hints or "  - なし"}

[守ること]
- date は今日より後の YYYY-MM-DD、time は HH:MM（7:00〜22:00 の間）
- reason は利用者に話しかける日本語の1〜2文（80文字以内）。なぜその日なのかが伝わるように。お店が分かっていれば、場所にもふれる
- 締切や期間の終わりを過ぎてしまう日は選ばない
- basis は、その日にした一番の理由（{", ".join(BASIS)}）"""
    data = llm.generate_json(prompt, RECOMMEND_SCHEMA)
    out, days = [], set()
    for rec in data.get("recommendations", []) if isinstance(data.get("recommendations"), list) else []:
        if not isinstance(rec, dict):
            continue
        d = _date(rec.get("date"))
        try:
            hh, mm = (int(x) for x in str(rec.get("time", "20:00")).split(":")[:2])
            at = datetime.combine(d, time(min(max(hh, 7), 22), mm if 0 <= mm < 60 else 0), tzinfo=TZ) if d else None
        except ValueError:
            at = None
        reason = _text(rec.get("reason"), 120)
        if not at or not reason or at <= now or at > now + timedelta(days=365) or at.date() in days:
            continue  # 過去・1年より先・同じ日・理由なし は使わない
        days.add(at.date())
        out.append({"remindAt": at, "reason": reason, "basis": rec.get("basis") if rec.get("basis") in BASIS else "other"})
    if not out:
        raise ValueError("AI の推薦が使えませんでした")
    return sorted(out, key=lambda r: r["remindAt"])[:3]


# ---------------- 3. 推薦：近くのお店があるときの一言 ----------------

NEARBY_SCHEMA = {
    "type": "OBJECT",
    "properties": {"messages": {"type": "ARRAY", "items": {
        "type": "OBJECT", "properties": {"itemId": {"type": "INTEGER"}, "reason": {"type": "STRING"}}, "required": ["itemId", "reason"]}}},
    "required": ["messages"],
}


def nearby_reasons(matches: list[dict]) -> dict[int, str]:
    """近くにお店がある欲しいものごとに、通知の一言を考える。{itemId: 文}。"""
    lines = "\n".join(f'- itemId={m["itemId"]}：「{m["title"] or "欲しいもの"}」（{genre_label(m["genre"])}）→ {m["placeName"]}まで約{m["distanceM"]}m'
                      for m in matches)
    prompt = f"""利用者は今、次のお店の近くにいます。それぞれの欲しいものについて、立ち寄りたくなる通知の一言（日本語・60文字以内）を考えてください。
押しつけがましくせず、お店の名前と距離にふれてください。
{lines}"""
    data = llm.generate_json(prompt, NEARBY_SCHEMA)
    ids = {m["itemId"] for m in matches}
    out = {}
    for msg in data.get("messages", []) if isinstance(data.get("messages"), list) else []:
        if isinstance(msg, dict) and msg.get("itemId") in ids and (text := _text(msg.get("reason"), 80)):
            out[msg["itemId"]] = text
    return out
