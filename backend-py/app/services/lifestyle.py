"""生活スタイルの診断：5問の質問と、答えから結果を作るしくみ（画面の質問と同じ）。"""

import re

QUESTIONS = [
    {"id": "payday", "text": "お給料日はいつごろ？", "multiple": False,
     "choices": ["1日", "5日", "10日", "15日", "20日", "25日", "月末", "決まっていない"]},
    {"id": "favoriteGenres", "text": "よく見るジャンルは？", "multiple": True,
     "choices": ["ファッション", "コスメ", "暮らし", "ガジェット", "本・文具", "その他"]},
    {"id": "shoppingStyle", "text": "お買いものはどんなスタイル？", "multiple": False,
     "choices": ["ネットで見ることが多い", "お店で見ることが多い", "どちらも同じくらい"]},
    {"id": "budgetTiming", "text": "買うものを考えることが多いのは？", "multiple": False,
     "choices": ["給料日のあと", "月の真ん中", "月末ごろ", "特に決まっていない"]},
    {"id": "reminderTime", "text": "お知らせを見るならいつがいい？", "multiple": False,
     "choices": ["朝（6〜11時）", "昼（11〜18時）", "夜（18〜22時）"]},
]
BY_ID = {q["id"]: q for q in QUESTIONS}


def payday_from(value: str) -> int:
    """「25日」→ 25、「月末」→ 31、「決まっていない」→ 25（仮の値）。"""
    if "月末" in value:
        return 31
    m = re.search(r"(\d{1,2})", value)
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 31 else 25


def diagnose(answers: list[dict]) -> tuple[int, dict]:
    """5問の答えから、給料日と好み（preferences）を作る。答えがおかしければ ValueError。"""
    given = {a["questionId"]: a["value"] for a in answers}
    if set(given) != set(BY_ID):
        raise ValueError("5問すべてに答えてください（questionId：" + "・".join(BY_ID) + "）。")
    preferences: dict = {}
    for qid, value in given.items():
        question = BY_ID[qid]
        values = [v.strip() for v in re.split(r"[、,]", value) if v.strip()] if question["multiple"] else [value]
        bad = [v for v in values if v not in question["choices"]]
        if bad:
            raise ValueError(f"「{question['text']}」の答え「{bad[0]}」は選べません。")
        preferences[qid] = values if question["multiple"] else value
    return payday_from(given["payday"]), preferences
