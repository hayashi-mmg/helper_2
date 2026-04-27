"""買い物リスト生成ロジックの単体テスト。"""
import uuid
from dataclasses import dataclass, field

import pytest

from app.services.shopping_list_generator import (
    AggregatedIngredient,
    _aggregate_ingredients,
    _build_quantity_text,
    _SKIP_INGREDIENTS,
)


@dataclass
class FakeIngredient:
    """テスト用の食材スタブ（SQLAlchemy モデルの属性を模倣）。"""
    id: uuid.UUID
    recipe_id: uuid.UUID
    name: str
    quantity: str | None
    category: str = "その他"
    sort_order: int = 0


class TestAggregateIngredients:
    """_aggregate_ingredients のテスト。"""

    def test_aggregate_same_name(self):
        """同名食材の集約。"""
        r1 = uuid.uuid4()
        r2 = uuid.uuid4()
        name_map = {r1: "照り焼き", r2: "親子丼"}

        ingredients = [
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="鶏もも肉", quantity="300g", category="肉類"),
            FakeIngredient(id=uuid.uuid4(), recipe_id=r2, name="鶏もも肉", quantity="200g", category="肉類"),
        ]

        result = _aggregate_ingredients(ingredients, name_map)
        assert len(result) == 1
        agg = result[0]
        assert agg.name == "鶏もも肉"
        assert len(agg.recipe_names) == 2
        assert "照り焼き" in agg.recipe_names
        assert "親子丼" in agg.recipe_names

    def test_aggregate_different_ingredients(self):
        """異なる食材は別々に。"""
        r1 = uuid.uuid4()
        name_map = {r1: "テストレシピ"}

        ingredients = [
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="鶏もも肉", quantity="300g"),
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="しょうゆ", quantity="大さじ2"),
        ]

        result = _aggregate_ingredients(ingredients, name_map)
        assert len(result) == 2

    def test_aggregate_no_quantity(self):
        """数量なしの食材。"""
        r1 = uuid.uuid4()
        name_map = {r1: "テスト"}

        ingredients = [
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="塩", quantity=None),
        ]

        result = _aggregate_ingredients(ingredients, name_map)
        assert len(result) == 1
        assert result[0].quantities == []

    def test_aggregate_empty_list(self):
        """空リスト。"""
        result = _aggregate_ingredients([], {})
        assert result == []

    def test_skip_ingredients_filtered(self):
        """水などの購入不要食材がスキップされること。"""
        r1 = uuid.uuid4()
        name_map = {r1: "テストレシピ"}

        ingredients = [
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="鶏もも肉", quantity="300g", category="肉類"),
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="水", quantity="200ml", category="その他"),
            FakeIngredient(id=uuid.uuid4(), recipe_id=r1, name="お湯", quantity="500ml", category="その他"),
        ]

        result = _aggregate_ingredients(ingredients, name_map)
        assert len(result) == 1
        assert result[0].name == "鶏もも肉"

    def test_all_skip_ingredients_defined(self):
        """スキップリストに必要な食材が含まれていること。"""
        expected = {"水", "氷", "お湯", "熱湯", "ぬるま湯", "冷水"}
        assert _SKIP_INGREDIENTS == expected


class TestBuildQuantityText:
    """_build_quantity_text のテスト。"""

    def test_single_quantity(self):
        agg = AggregatedIngredient(name="鶏もも肉", category="肉類", quantities=[("照り焼き", "300g")])
        text = _build_quantity_text(agg)
        assert text == "300g"

    def test_single_quantity_recipe_name_with_space(self):
        """レシピ名にスペースが含まれても数量は混入しないこと。"""
        agg = AggregatedIngredient(
            name="本つゆ", category="調味料",
            quantities=[("おむすびの具材 本つゆ胡麻チーおかか", "大さじ4")],
        )
        text = _build_quantity_text(agg)
        assert text == "大さじ4"

    def test_multiple_quantities(self):
        agg = AggregatedIngredient(
            name="鶏もも肉", category="肉類",
            quantities=[("照り焼き", "300g"), ("親子丼", "200g")],
        )
        text = _build_quantity_text(agg)
        assert "照り焼き 300g" in text
        assert "親子丼 200g" in text

    def test_no_quantity(self):
        agg = AggregatedIngredient(name="塩", category="調味料", quantities=[])
        text = _build_quantity_text(agg)
        assert text is None
