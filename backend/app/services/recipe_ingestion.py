"""レシピ食材テキストのパースとカテゴリ判定の共通ロジック。

`scripts/seed_recipes.py` および `crud/admin_menu_import.py` から共有される。
"""

from __future__ import annotations

import re

# 食材カテゴリ自動判定
_CAT_KW: dict[str, list[str]] = {
    "肉類": ["肉", "ひき肉", "ベーコン", "ハム", "ウインナー", "ささみ", "鶏", "豚", "牛"],
    "魚介類": ["鮭", "サーモン", "エビ", "えび", "牡蠣", "タラ", "たら", "鱈", "ツナ", "マグロ", "鰹", "ニシン", "アンチョビ", "シーチキン", "白子"],
    "野菜": ["玉ねぎ", "ねぎ", "ネギ", "にんじん", "じゃがいも", "大根", "ごぼう", "ピーマン", "ナス", "茄子", "アスパラ", "レタス", "トマト", "きゅうり", "ほうれん草", "小松菜", "水菜", "キャベツ", "もやし", "にら", "オクラ", "たけのこ", "筍", "しいたけ", "エリンギ", "舞茸", "しめじ", "えのき", "大葉", "パセリ", "ミョウガ", "わかめ", "コーン"],
    "卵・乳製品": ["卵", "玉子", "チーズ", "バター", "牛乳", "生クリーム", "温泉卵", "豆乳", "豆腐"],
    "調味料": ["醤油", "しょうゆ", "みりん", "酒", "砂糖", "塩", "胡椒", "コショウ", "油", "オリーブオイル", "ごま油", "酢", "味噌", "だし", "コンソメ", "ソース", "ケチャップ", "マヨネーズ", "ワサビ", "わさび", "ドレッシング", "めんつゆ", "味の素", "オイスターソース", "味覇", "鶏がらスープ", "片栗粉", "薄力粉", "小麦粉", "米粉", "粉チーズ", "カレールー", "カレー粉", "ラー油", "レモン汁", "レモン", "にんにく", "ニンニク", "しょうが", "生姜", "唐辛子", "鷹の爪", "ブラックペッパー", "白ごま", "すりごま", "梅肉", "ポン酢", "香味ペースト", "本つゆ"],
    "穀類": ["米", "ご飯", "ごはん", "パスタ", "うどん", "パン", "春巻", "ライスペーパー", "麺"],
}


def guess_ingredient_category(name: str) -> str:
    for cat, kws in _CAT_KW.items():
        for kw in kws:
            if kw in name:
                return cat
    return "その他"


def parse_ingredients_text(text: str | None) -> list[dict]:
    """`"鶏もも肉 300g\\nしょうゆ 大さじ2"` のようなテキストを構造化食材リストに変換する。"""
    if not text:
        return []
    results = []
    for i, line in enumerate(text.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"\s+", line, maxsplit=1)
        name = parts[0]
        quantity = parts[1] if len(parts) > 1 else None
        results.append(
            {
                "name": name,
                "quantity": quantity,
                "category": guess_ingredient_category(name),
                "sort_order": i + 1,
            }
        )
    return results
