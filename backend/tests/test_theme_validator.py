"""ThemeValidator の単体テスト。

docs/theme_system_implementation_plan.md §5.2.1
"""
import copy

import pytest

from app.services.theme_presets import CALM, HIGH_CONTRAST, STANDARD, WARM
from app.services.theme_validator import (
    ThemeValidationError,
    _hex_to_rgb,
    contrast_ratio,
    resolve_color,
    validate_theme_definition,
)


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------
def test_hex_to_rgb_basic():
    assert _hex_to_rgb("#ffffff") == (255, 255, 255)
    assert _hex_to_rgb("#000000") == (0, 0, 0)
    assert _hex_to_rgb("#1976d2") == (25, 118, 210)


def test_hex_to_rgb_invalid():
    with pytest.raises(ValueError):
        _hex_to_rgb("blue")
    with pytest.raises(ValueError):
        _hex_to_rgb("#abc")


def test_contrast_ratio_known_pairs():
    # 白 vs 黒 = 21.0 ± 小数誤差
    assert contrast_ratio("#ffffff", "#000000") == pytest.approx(21.0, abs=0.01)
    # 同色 = 1.0
    assert contrast_ratio("#1976d2", "#1976d2") == pytest.approx(1.0, abs=0.01)


def test_contrast_ratio_text_on_white():
    # 既知の実測値: neutral.800 (#212121) vs white ≈ 16.1
    assert contrast_ratio("#212121", "#ffffff") == pytest.approx(16.1, abs=0.2)


def test_resolve_color_direct_hex():
    assert resolve_color("#1976d2", STANDARD) == "#1976d2"


def test_resolve_color_token_ref():
    assert resolve_color("{colors.brand.500}", STANDARD) == "#1976d2"


def test_resolve_color_unresolved():
    with pytest.raises(ValueError):
        resolve_color("{colors.brand.999}", STANDARD)


# ---------------------------------------------------------------------------
# プリセット 4 種が合格
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "preset,key",
    [(STANDARD, "standard"), (HIGH_CONTRAST, "high-contrast"), (WARM, "warm"), (CALM, "calm")],
)
def test_builtin_preset_passes_validation(preset, key):
    parsed = validate_theme_definition(preset)
    assert parsed.id == key


# ---------------------------------------------------------------------------
# スキーマ違反
# ---------------------------------------------------------------------------
def test_missing_schema_version():
    bad = copy.deepcopy(STANDARD)
    del bad["schema_version"]
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    assert any("schema_version" in e["field"] for e in exc.value.errors)


def test_invalid_density():
    bad = copy.deepcopy(STANDARD)
    bad["density"] = "invalid"
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    assert any("density" in e["field"] for e in exc.value.errors)


def test_brand_missing_500():
    bad = copy.deepcopy(STANDARD)
    bad["colors"]["brand"].pop("500")
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    assert any("brand" in e["field"] for e in exc.value.errors)


# ---------------------------------------------------------------------------
# フォントサイズ境界値
# ---------------------------------------------------------------------------
def test_font_size_17_rejected():
    bad = copy.deepcopy(STANDARD)
    bad["fonts"]["baseSizePx"] = 17
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    codes = [e["code"] for e in exc.value.errors]
    assert "font_size_too_small" in codes


def test_font_size_18_accepted():
    ok = copy.deepcopy(STANDARD)
    ok["fonts"]["baseSizePx"] = 18
    validate_theme_definition(ok)


# ---------------------------------------------------------------------------
# コントラスト比境界値
# ---------------------------------------------------------------------------
def test_text_contrast_too_low():
    bad = copy.deepcopy(STANDARD)
    bad["semanticTokens"]["text.primary"] = "#bbbbbb"  # 灰色で白地に対し低コントラスト
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    codes = [e["code"] for e in exc.value.errors]
    assert "text_bg_contrast_too_low" in codes


def test_on_brand_contrast_too_low():
    bad = copy.deepcopy(STANDARD)
    bad["semanticTokens"]["text.onBrand"] = "#bbcbff"  # 淡い青、brand.500 に対し低コントラスト
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    codes = [e["code"] for e in exc.value.errors]
    assert "on_brand_contrast_too_low" in codes


def test_border_focus_contrast_too_low():
    bad = copy.deepcopy(STANDARD)
    bad["semanticTokens"]["border.focus"] = "#f5f5f5"  # 背景 neutral.50 とほぼ同色
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    codes = [e["code"] for e in exc.value.errors]
    assert "border_focus_contrast_too_low" in codes


# ---------------------------------------------------------------------------
# 未解決トークン参照
# ---------------------------------------------------------------------------
def test_unresolved_token_reference():
    bad = copy.deepcopy(STANDARD)
    bad["semanticTokens"]["text.primary"] = "{colors.nonexistent.500}"
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    codes = [e["code"] for e in exc.value.errors]
    assert "unresolved_token_reference" in codes


# ---------------------------------------------------------------------------
# 必須トークン欠落
# ---------------------------------------------------------------------------
def test_missing_required_semantic_tokens():
    bad = copy.deepcopy(STANDARD)
    bad["semanticTokens"].pop("text.primary")
    with pytest.raises(ThemeValidationError) as exc:
        validate_theme_definition(bad)
    codes = [e["code"] for e in exc.value.errors]
    assert "missing_token" in codes
