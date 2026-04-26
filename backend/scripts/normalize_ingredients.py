"""recipe_ingredients テーブルの表記揺れを一括正規化するスクリプト。

適用内容:
1. 同義語の統一（ニンニク → にんにく、しょう油 → 醤油、など）
2. カテゴリの修正（牛乳: 肉類 → 卵・乳製品、など明らかな誤分類）
3. 名前に埋め込まれた括弧修飾と数量の剥離
   （例: '鶏むね肉（皮なし）1枚（250g）' → name='鶏むね肉', quantity に '1枚, 250g' を付与）

使い方（コンテナ内から）:
    docker compose exec backend python scripts/normalize_ingredients.py --dry-run
    docker compose exec backend python scripts/normalize_ingredients.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

# FastAPI アプリのモジュールを import できるように
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.db.models.recipe_ingredient import RecipeIngredient


# ---------------------------------------------------------------------------
# 正規化ルール
# ---------------------------------------------------------------------------

# クリーン名（paren/trailing-qty 除去後）に対する同義語統一
SYNONYMS: dict[str, str] = {
    # にんにく
    "ニンニク": "にんにく",
    "ニンニクチューブ": "にんにく",
    "にんにくチューブ": "にんにく",
    "おろしにんにく": "にんにく",
    "すりおろしニンニク": "にんにく",
    "ニンニクすりおろし": "にんにく",
    # しょうが
    "おろししょうが": "しょうが",
    "すりおろし生姜": "しょうが",
    "しょうがチューブ": "しょうが",
    "生姜": "しょうが",
    # 醤油
    "しょう油": "醤油",
    # 卵
    "玉子": "卵",
    # ご飯
    "ごはん": "ご飯",
    # かつお節
    "かつおぶし": "かつお節",
    "鰹節": "かつお節",
    # チーズ
    "溶けるチーズ": "とろけるチーズ",
    # わさび
    "ワサビ": "わさび",
    # 胡椒
    "黒こしょう": "胡椒",
    "黒胡椒": "胡椒",
    "粗挽き黒こしょう": "胡椒",
    "粗挽き黒胡椒": "胡椒",
    "ブラックペッパー": "胡椒",
    # 塩コショウ
    "塩こしょう": "塩コショウ",
    "塩胡椒": "塩コショウ",
    # 玉ねぎ
    "新たまねぎ": "新玉ねぎ",
    # 薬味用細ねぎ（白ネギは別物として保持）
    "青ネギ": "小ねぎ",
    "小ネギ": "小ねぎ",
    "刻みネギ": "小ねぎ",
    "万能ねぎ": "小ねぎ",
    # エビ（調理上の下処理違いはすべて「エビ」に）
    "むきエビ": "エビ",
    "無頭エビ": "エビ",
    # 豚こま切れ肉
    "豚の小間切れ肉": "豚こま切れ肉",
    "豚小間切れ肉": "豚こま切れ肉",
    # アスパラ
    "アスパラガス": "アスパラ",
    # アンチョビ
    "アンチョビフィレ": "アンチョビ",
    # シーチキン(商品名) → ツナ缶
    "シーチキン": "ツナ缶",
    "ツナ": "ツナ缶",
}

# クリーン名 → カテゴリ（明らかな誤分類を正す）
CATEGORY_OVERRIDE: dict[str, str] = {
    "牛乳": "卵・乳製品",
    "豆乳": "卵・乳製品",
    "梅肉ソース": "調味料",
    "ベビーチーズ生ハム入り": "卵・乳製品",
    "焼肉のタレ": "調味料",
    "鶏がらスープの素": "調味料",
    "牡蠣だし醤油": "調味料",
    "びんちょう鮪": "魚介類",
    "黒アワビ": "魚介類",
    "サラダ菜": "野菜",
    "パプリカ": "野菜",
    "粉末パセリ": "調味料",
    "まいたけ": "野菜",
    "エノキだけ": "野菜",
    "胡椒": "調味料",
    "塩コショウ": "調味料",
    "かつお節": "調味料",
    "ツナ缶": "魚介類",
}

# ---------------------------------------------------------------------------
# 名前から括弧修飾と末尾数量を剥離するロジック（shopping_organizer と同等）
# ---------------------------------------------------------------------------

_PAREN_QUALIFIER = re.compile(r"[（(][^）)]*[）)]")
_QUANTITY_HINT = re.compile(r"[0-9０-９]|適量|少々|大さじ|小さじ|カップ|[gkml]|cc|kg")
_TRAILING_QUANTITY = re.compile(
    r"\s*(?:"
    r"各?(?:大さじ|小さじ|カップ)\s*[0-9０-９.／/〜\-]+(?:分|くらい)?"
    r"|各?[0-9０-９.／/〜\-]+\s*(?:個|枚|本|束|パック|袋|切れ|片|丁|尾|缶|粒|cc|ml|L|g|kg|合|さじ|カップ|玉|つまみ)(?:分|くらい)?"
    r"|[0-9０-９.／/〜\-]+(?:分|くらい)?"
    r"|適量|少々|お好み|適宜|あれば|ふたつまみ|ひとつまみ|好きなだけ|少量|くらい"
    r")\s*$"
)


def clean_name_with_qty(name: str) -> tuple[str, list[str]]:
    """名前から括弧修飾と末尾数量を剥離し、(cleaned_name, extracted_qtys) を返す。"""
    extracted: list[str] = []

    def _paren(m: re.Match) -> str:
        inner = m.group(0)[1:-1].strip()
        if _QUANTITY_HINT.search(inner):
            extracted.append(inner)
        return ""

    n = _PAREN_QUALIFIER.sub(_paren, name)
    # 末尾数量を繰り返し除去
    prev = None
    while prev != n:
        prev = n
        m = _TRAILING_QUANTITY.search(n)
        if m and m.end() == len(n):
            q = m.group(0).strip()
            if q:
                extracted.append(q)
            n = n[: m.start()].rstrip()
    return n.strip(), extracted


def normalize_ingredient(name: str, quantity: str | None, category: str) -> tuple[str, str | None, str] | None:
    """1行分の (name, quantity, category) を正規化し、
    変更があれば新しいタプルを、変更なければ None を返す。
    """
    # 1. 括弧と末尾数量を剥離
    cleaned, extracted_qtys = clean_name_with_qty(name)
    # 2. 同義語適用
    new_name = SYNONYMS.get(cleaned, cleaned)
    # 空文字になってしまった場合はスキップ（保持）
    if not new_name:
        return None
    # 3. カテゴリ強制上書き（既知の食材のみ）
    new_category = CATEGORY_OVERRIDE.get(new_name, category)
    # 4. 名前から救出した数量を quantity にマージ
    new_quantity = quantity
    numeric_extracts = [q for q in extracted_qtys if re.search(r"[0-9０-９]", q)]
    if numeric_extracts:
        joined = "、".join(numeric_extracts)
        if new_quantity and new_quantity.strip():
            # 既存 quantity に含まれていなければ追記
            if joined not in new_quantity:
                new_quantity = f"{new_quantity}、{joined}"
        else:
            new_quantity = joined
        if new_quantity and len(new_quantity) > 50:
            new_quantity = new_quantity[:50]

    if new_name == name and new_category == category and (new_quantity or None) == (quantity or None):
        return None

    return (new_name, new_quantity, new_category)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

async def main(apply: bool) -> None:
    async with async_session() as db:
        result = await db.execute(select(RecipeIngredient))
        rows = list(result.scalars().all())

        changes: list[tuple[RecipeIngredient, str, str | None, str]] = []
        for row in rows:
            result_tuple = normalize_ingredient(row.name, row.quantity, row.category)
            if result_tuple is None:
                continue
            new_name, new_qty, new_cat = result_tuple
            changes.append((row, new_name, new_qty, new_cat))

        print(f"対象行数: {len(rows)}")
        print(f"変更予定: {len(changes)}")
        print()

        # カテゴリ別に表示
        print("--- 変更内容 ---")
        for row, new_name, new_qty, new_cat in changes:
            name_change = f"{row.name!r} → {new_name!r}" if row.name != new_name else f"(name) {row.name}"
            cat_change = f"[{row.category} → {new_cat}]" if row.category != new_cat else f"[{row.category}]"
            qty_old = row.quantity or ""
            qty_new = new_qty or ""
            qty_change = ""
            if qty_old != qty_new:
                qty_change = f"  qty: {qty_old!r} → {qty_new!r}"
            print(f"  {name_change}  {cat_change}{qty_change}")

        if not apply:
            print()
            print("(dry-run のため DB は変更していません)")
            return

        # 適用
        print()
        print("変更を適用中…")
        for row, new_name, new_qty, new_cat in changes:
            row.name = new_name
            row.quantity = new_qty
            row.category = new_cat
        await db.commit()
        print(f"完了: {len(changes)} 行を更新しました")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実際にDBを更新する")
    parser.add_argument("--dry-run", action="store_true", help="変更候補を表示のみ (default)")
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
