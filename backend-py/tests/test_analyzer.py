"""services/analyzer.py のテスト（python -m pytest で実行）。"""

from app.services.analyzer import analyze, find_genre, find_price, find_title, make_description


def test_価格を読み取る():
    assert find_price("税込 3,980円") == 3980
    assert find_price("¥1,200") == 1200
    assert find_price("２，５００円") == 2500  # 全角
    assert find_price("価格未定") is None


def test_時刻や価格だけの行は商品名にしない():
    assert find_title("12:34\n80%\n¥3,980\nふわふわニットカーディガン") == "ふわふわニットカーディガン"
    assert find_title("12:34\n¥3,980") is None


def test_キーワードでジャンルを分ける():
    assert find_genre("限定コラボ ぬいぐるみ 受注開始") == "goods"
    assert find_genre("ワイヤレスイヤホン Bluetooth") == "gadget"
    assert find_genre("ウォータリーティント リップ") == "cosme"
    assert find_genre("北欧風 フロアライト 照明") == "interior"
    assert find_genre("今日は晴れ") == "other"


def test_説明文を作る():
    text = "限定アクスタ\nちいかわ×〇〇カフェ\n開催期間 11/1〜11/30"
    assert make_description(text, "goods") == "キャラクター・グッズ｜ちいかわ×〇〇カフェ 開催期間 11/1〜11/30"
    assert make_description("限定アクスタ", "goods") is None


def test_まとめて解析すると場所も埋まる():
    values = analyze("新作ティント リップ\n¥1,650")
    assert values["genre"] == "cosme"
    assert values["place_category"] == "ドラッグストア"
    assert values["price"] == 1650
    assert values["place_name"] is None  # 具体的なお店は、今は空


def test_文字がなければ埋めない():
    values = analyze("")
    assert values["title"] is None
    assert values["description"] is None
    assert values["price"] is None
    assert values["genre"] == "other"
