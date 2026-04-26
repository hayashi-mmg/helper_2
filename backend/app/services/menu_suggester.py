"""AI献立提案サービス。

既存のRecipeカタログをOllamaに渡し、1週間分の献立を返させる。
Ollamaが返すJSONはDB保存せず、レスポンスとして返すのみ。
利用者が画面で確認した後、既存の ``PUT /menus/week`` で適用する。
"""

import json
import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recipe import Recipe
from app.schemas.menu_suggestion import (
    MenuSuggestionRequest,
    SuggestedMealSlot,
    SuggestedRecipeRef,
    WeeklyMenuSuggestionResponse,
)
from app.services.llm_client import OllamaClient, OllamaInvalidJSONError

logger = logging.getLogger(__name__)

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
RECIPE_TYPES = ("主菜", "副菜", "汁物", "ご飯", "その他")

SYSTEM_PROMPT = (
    "あなたは高齢者向け献立を提案する管理栄養士です。"
    "必ず指定されたJSONスキーマのみで回答し、説明文やコードブロックは出力しないでください。"
    "主菜・副菜・汁物・ご飯のバランスを意識し、柔らかく消化が良く、塩分控えめの和食中心の献立を組み立てます。"
    "与えられたレシピ一覧の recipe_id のみを使用し、架空のレシピは作らないでください。"
)


class RecipeCatalogEmptyError(Exception):
    """Recipeカタログが空で献立提案できない状態。"""


class SuggestionValidationError(Exception):
    """Ollamaの応答が期待するスキーマ/制約を満たさない。"""


async def _load_recipe_catalog(db: AsyncSession, user_id: uuid.UUID) -> list[Recipe]:
    result = await db.execute(
        select(Recipe).where(Recipe.user_id == user_id, Recipe.is_active.is_(True))
    )
    return list(result.scalars().all())


MAX_CATALOG_SIZE = 60  # トークン上限保護


def _make_alias_map(recipes: list[Recipe]) -> dict[str, Recipe]:
    """レシピにトークン節約用の短いエイリアス (r01..) を割り当てる。"""
    return {f"r{i + 1:02d}": r for i, r in enumerate(recipes)}


def _build_user_prompt(
    recipes: list[Recipe],
    week_start: date,
    request: MenuSuggestionRequest,
    alias_map: dict[str, Recipe] | None = None,
) -> str:
    # UUID(36字)を直接モデルに渡すと出力トークンを大量消費するため、
    # 短いエイリアス(r01..)を割当てる。サーバー側で元のUUIDに復元する。
    alias_map = alias_map if alias_map is not None else _make_alias_map(recipes)
    catalog_lines = "\n".join(
        f"{alias}|{r.name}|{r.type}|{r.cooking_time}" for alias, r in alias_map.items()
    )
    dietary = "、".join(request.dietary_restrictions) if request.dietary_restrictions else "指定なし"
    avoid = "、".join(request.avoid_ingredients) if request.avoid_ingredients else "指定なし"
    notes = request.notes or "特になし"

    # 出力例には7日分すべてのキーを含める（モデルが1日で打ち切らないよう）
    empty_slot = {"breakfast": [], "dinner": []}
    example_monday = {
        "breakfast": [{"recipe_id": "r01", "recipe_type": "主菜"}],
        "dinner": [{"recipe_id": "r02", "recipe_type": "主菜"}],
    }
    output_example = {
        "menus": {
            "monday": example_monday,
            "tuesday": empty_slot,
            "wednesday": empty_slot,
            "thursday": empty_slot,
            "friday": empty_slot,
            "saturday": empty_slot,
            "sunday": empty_slot,
        }
    }

    return (
        "【利用可能なレシピ一覧】 形式: recipe_id|name|recipe_type|cooking_time\n"
        f"{catalog_lines}\n\n"
        f"【今週の開始日】{week_start.isoformat()}（月曜）\n\n"
        "【必ず守るルール】\n"
        "- menus のキーは monday, tuesday, wednesday, thursday, friday, saturday, sunday の7つすべてを含めること（どの曜日も省略禁止）\n"
        "- 各曜日に朝食(breakfast)と夕食(dinner)の両方を埋める\n"
        "- 1食につき各 recipe_type は最大1品（主菜1、副菜1、汁物1、ご飯1 で計4品まで）\n"
        "- 同じ食事内で同じ recipe_type を重複させない\n"
        "- 主菜の連続重複（同じレシピが複数日続く）を避ける\n"
        "- recipe_type は 主菜 / 副菜 / 汁物 / ご飯 / その他 のいずれか\n"
        "- 指定タイプのレシピがカタログに存在しない場合はそのスロットを省略してよい（架空のIDは作らない）\n"
        "- recipe_type はカタログに記載された各レシピの本来のタイプと一致させること（主菜のレシピを副菜として使わない）\n\n"
        "【好み】\n"
        f"- 食事制限: {dietary}\n"
        f"- 避けたい食材: {avoid}\n"
        f"- その他ご要望: {notes}\n\n"
        "【出力形式】\n"
        "下記スキーマに従い、JSONのみを出力してください（説明文やコードブロックは禁止）。\n"
        "必ず monday〜sunday の7日分すべてのキーを含め、それぞれ breakfast/dinner を埋めてください。\n"
        "tuesday 以降を省略したり空にしたりしてはいけません。\n\n"
        f"{json.dumps(output_example, ensure_ascii=False, indent=2)}\n\n"
        "※ 上記は例です。実際は tuesday〜sunday もすべて monday と同様に埋めてください。\n"
        "※ recipe_id は上記レシピ一覧の r01 形式の値のみ使用可。"
    )


def _validate_and_map(
    raw: dict,
    alias_map: dict[str, Recipe],
    week_start: date,
) -> WeeklyMenuSuggestionResponse:
    """Ollamaの応答(エイリアスID)を検証し、本来のUUIDを持つレスポンスに復元する。

    DB 制約 UNIQUE(menu_id, day, meal_type, recipe_type) を満たすため、
    各食事内で recipe_type が重複した場合は最初のものを採用する（残りは黙って破棄）。
    モデルが返した recipe_type は無視し、カタログにある本来の Recipe.type を用いる。
    """
    if not isinstance(raw, dict) or "menus" not in raw or not isinstance(raw["menus"], dict):
        raise SuggestionValidationError("menus フィールドがありません")

    menus_out: dict[str, SuggestedMealSlot] = {}
    for day in DAYS:
        day_data = raw["menus"].get(day, {})
        if not isinstance(day_data, dict):
            day_data = {}

        slot_out = {"breakfast": [], "dinner": []}
        for meal in ("breakfast", "dinner"):
            entries = day_data.get(meal, [])
            if not isinstance(entries, list):
                entries = []
            seen_types: set[str] = set()
            for item in entries:
                if not isinstance(item, dict):
                    continue
                alias = item.get("recipe_id")
                if alias not in alias_map:
                    # 未知の recipe_id は黙って無視（ハルシネーション耐性）
                    continue
                recipe = alias_map[alias]
                # モデルの recipe_type ラベルは信頼せず、カタログの本来の type を使う
                canonical_type = recipe.type
                if canonical_type not in RECIPE_TYPES:
                    continue
                if canonical_type in seen_types:
                    # 同じ食事内での recipe_type 重複は DB 制約違反になるため破棄
                    continue
                seen_types.add(canonical_type)
                slot_out[meal].append(
                    SuggestedRecipeRef(
                        recipe_id=str(recipe.id),
                        name=recipe.name,
                        recipe_type=canonical_type,
                        cooking_time=recipe.cooking_time,
                    )
                )
        menus_out[day] = SuggestedMealSlot(**slot_out)

    return WeeklyMenuSuggestionResponse(
        week_start=week_start,
        menus=menus_out,
        rationale=None,
    )


async def suggest_weekly_menu(
    db: AsyncSession,
    user_id: uuid.UUID,
    request: MenuSuggestionRequest,
    client: OllamaClient | None = None,
) -> WeeklyMenuSuggestionResponse:
    recipes = await _load_recipe_catalog(db, user_id)
    if not recipes:
        raise RecipeCatalogEmptyError()

    # 大規模カタログはトークン超過を招くため上限を設ける
    if len(recipes) > MAX_CATALOG_SIZE:
        recipes = recipes[:MAX_CATALOG_SIZE]

    alias_map = _make_alias_map(recipes)
    user_prompt = _build_user_prompt(recipes, request.week_start, request, alias_map)

    client = client or OllamaClient()
    raw = await client.chat_json(SYSTEM_PROMPT, user_prompt)

    return _validate_and_map(raw, alias_map, request.week_start)
