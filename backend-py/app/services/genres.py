"""ジャンルの一覧、自動で分けるときのキーワード、ジャンルごとのお店の種類。"""

GENRES = [
    {"id": "cosme", "label": "コスメ", "place": "ドラッグストア",
     "keywords": ["リップ", "ティント", "ファンデ", "コスメ", "アイシャドウ", "マスカラ", "化粧水", "美容液", "乳液", "チーク",
                  "アイライナー", "日焼け止め", "スキンケア", "メイク", "パレット", "香水", "ネイル"]},
    {"id": "fashion", "label": "ファッション", "place": "アパレルショップ",
     "keywords": ["ワンピース", "スカート", "パンツ", "ニット", "カーディガン", "ジャケット", "コート", "シャツ", "ブラウス", "スニーカー",
                  "ブーツ", "バッグ", "トップス", "デニム", "パーカー", "コーデ", "アクセサリー", "ピアス", "ネックレス", "帽子", "古着", "腕時計"]},
    {"id": "gadget", "label": "ガジェット・家電", "place": "家電量販店",
     "keywords": ["イヤホン", "ヘッドホン", "キーボード", "マウス", "モニター", "ディスプレイ", "充電器", "ケーブル", "スマホ", "タブレット",
                  "パソコン", "SSD", "USB", "Bluetooth", "ワイヤレス", "スピーカー", "カメラ", "ガジェット", "家電", "コーヒーメーカー", "ドリッパー"]},
    {"id": "interior", "label": "家具・インテリア", "place": "家具・インテリアショップ",
     "keywords": ["ソファ", "ラグ", "カーテン", "照明", "ライト", "ランプ", "テーブル", "チェア", "椅子", "棚", "ラック", "収納",
                  "インテリア", "観葉植物", "ベッド", "マット", "花瓶", "雑貨"]},
    {"id": "goods", "label": "キャラクター・グッズ", "place": "キャラクターショップ・コラボ会場",
     "keywords": ["グッズ", "コラボ", "ぬいぐるみ", "アクスタ", "アクリルスタンド", "缶バッジ", "キーホルダー", "マスコット", "限定", "受注",
                  "予約", "くじ", "ガチャ", "トレカ", "ステッカー", "推し", "ペンライト"]},
    {"id": "book", "label": "本・漫画", "place": "本屋",
     "keywords": ["巻", "コミック", "漫画", "マンガ", "単行本", "文庫", "小説", "新刊", "書籍", "出版", "著者", "電子書籍", "ISBN"]},
    {"id": "food", "label": "飲食店", "place": "飲食店",
     "keywords": ["ラーメン", "カフェ", "レストラン", "ランチ", "ディナー", "メニュー", "営業時間", "定休日", "食べログ", "テイクアウト",
                  "居酒屋", "パンケーキ", "スイーツ", "ベーカリー", "店舗", "住所"]},
    {"id": "other", "label": "その他", "place": None, "keywords": []},
]


def genre_label(genre_id: str | None) -> str:
    """ジャンルの id から表示名を返す（例：cosme → コスメ）。"""
    return next((g["label"] for g in GENRES if g["id"] == genre_id), "その他")


def place_for(genre_id: str | None) -> str | None:
    """ジャンルから、買えそうなお店の種類を返す（例：cosme → ドラッグストア）。"""
    return next((g["place"] for g in GENRES if g["id"] == genre_id), None)


# ---- 場所（お店）と結びつけるための表 ----

# ジャンルのお店の種類を、地図（OpenStreetMap）のタグで表したもの。近くにこの種類のお店があるかを調べるのに使う
OSM_TAGS = {
    "cosme": [("shop", "chemist"), ("shop", "cosmetics"), ("amenity", "pharmacy")],
    "fashion": [("shop", "clothes"), ("shop", "shoes"), ("shop", "bag")],
    "gadget": [("shop", "electronics"), ("shop", "computer"), ("shop", "mobile_phone")],
    "interior": [("shop", "furniture"), ("shop", "interior_decoration"), ("shop", "houseware")],
    "goods": [("shop", "toys"), ("shop", "anime"), ("shop", "gift")],
    "book": [("shop", "books")],
    "food": [("amenity", "restaurant"), ("amenity", "cafe"), ("amenity", "fast_food")],
}

# スクショの文字に出てきたら「具体的なお店」として使う、よくあるお店の名前
STORE_NAMES = [
    "IKEA", "ニトリ", "無印良品", "ロフト", "LOFT", "ハンズ", "Francfranc", "3COINS", "PLAZA", "ドン・キホーテ",
    "マツモトキヨシ", "マツキヨ", "ウエルシア", "ツルハ", "スギ薬局", "サンドラッグ", "ココカラファイン",
    "ユニクロ", "UNIQLO", "GU", "ZARA", "しまむら", "H&M",
    "ヨドバシカメラ", "ビックカメラ", "ヤマダ電機", "ケーズデンキ", "Apple Store",
    "紀伊國屋書店", "TSUTAYA", "蔦屋書店", "ジュンク堂", "アニメイト", "ポケモンセンター", "ちいかわらんど", "ジャンプショップ",
]


def osm_tags_for(genre_id: str | None) -> list[tuple[str, str]]:
    """ジャンルから、地図で探すお店のタグを返す（例：cosme → shop=chemist など）。"""
    return OSM_TAGS.get(genre_id or "", [])
