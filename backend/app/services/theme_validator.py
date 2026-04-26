"""テーマ定義のバリデータ。

docs/theme_system_specification.md §3.2 に基づく:
- Pydantic ThemeDefinition スキーマ適合
- baseSizePx >= 18
- 本文コントラスト >= 4.5:1
- ブランド上テキスト >= 4.5:1
- 境界フォーカス >= 3:1
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from app.schemas.theme import ThemeDefinition


MIN_BODY_FONT_PX = 18
MIN_TEXT_CONTRAST = 4.5
MIN_BRAND_CONTRAST = 4.5
MIN_BORDER_FOCUS_CONTRAST = 3.0


_TOKEN_REF_RE = re.compile(r"^\{colors\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\}$")
_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")


class ThemeValidationError(Exception):
    """バリデーション失敗。`errors` にフィールド別の詳細を保持する。"""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__(str(errors))


# ---------------------------------------------------------------------------
# カラー解決
# ---------------------------------------------------------------------------
def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    m = _HEX_RE.match(hex_str)
    if not m:
        raise ValueError(f"invalid hex color: {hex_str}")
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    la = _relative_luminance(_hex_to_rgb(hex_a))
    lb = _relative_luminance(_hex_to_rgb(hex_b))
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)


def resolve_color(ref_or_hex: str, definition: dict[str, Any]) -> str:
    """`{colors.xxx.500}` 形式のトークン参照または直接の hex 値を hex に解決する。"""
    if _HEX_RE.match(ref_or_hex):
        return ref_or_hex.lower()
    m = _TOKEN_REF_RE.match(ref_or_hex)
    if not m:
        raise ValueError(f"unresolved_token_reference: {ref_or_hex}")
    palette, shade = m.group(1), m.group(2)
    try:
        value = definition["colors"][palette][shade]
    except (KeyError, TypeError):
        raise ValueError(f"unresolved_token_reference: {ref_or_hex}")
    if not _HEX_RE.match(value):
        # チェーン参照はサポートしない（複雑化回避）
        raise ValueError(f"unresolved_token_reference: {ref_or_hex}")
    return value.lower()


# ---------------------------------------------------------------------------
# 公開バリデータ
# ---------------------------------------------------------------------------
def validate_theme_definition(definition: dict[str, Any]) -> ThemeDefinition:
    """テーマ定義を検証する。成功時は ThemeDefinition を返す。

    失敗時は ThemeValidationError を送出する。呼び出し側は
    エラーコード + メッセージを 422 レスポンスに変換する。
    """
    errors: list[dict[str, str]] = []

    # 1) Pydantic スキーマ
    try:
        parsed = ThemeDefinition(**definition)
    except ValidationError as ve:
        for err in ve.errors():
            errors.append({
                "field": ".".join(str(p) for p in err["loc"]),
                "code": "schema_violation",
                "message": err["msg"],
            })
        raise ThemeValidationError(errors)

    # 2) baseSizePx >= 18
    if parsed.fonts.baseSizePx < MIN_BODY_FONT_PX:
        errors.append({
            "field": "fonts.baseSizePx",
            "code": "font_size_too_small",
            "message": f"本文フォントサイズは {MIN_BODY_FONT_PX}px 以上である必要があります(現在 {parsed.fonts.baseSizePx}px)",
        })

    tokens = parsed.semanticTokens or {}

    # 3) 本文コントラスト: text.primary vs bg.page
    _check_contrast(
        tokens, "text.primary", "bg.page", MIN_TEXT_CONTRAST,
        "text_bg_contrast_too_low", definition, errors,
    )

    # 4) ブランド上テキスト: text.onBrand vs colors.brand.500
    on_brand = tokens.get("text.onBrand")
    brand_500 = parsed.colors.brand.get("500")
    if on_brand and brand_500:
        try:
            a = resolve_color(on_brand, definition)
            b = resolve_color(brand_500, definition)
            ratio = contrast_ratio(a, b)
            if ratio < MIN_BRAND_CONTRAST:
                errors.append({
                    "field": "semanticTokens.text.onBrand",
                    "code": "on_brand_contrast_too_low",
                    "message": f"text.onBrand と brand.500 のコントラスト比は {MIN_BRAND_CONTRAST}:1 以上が必要です(現在 {ratio:.2f}:1)",
                })
        except ValueError as e:
            errors.append({
                "field": "semanticTokens.text.onBrand",
                "code": "unresolved_token_reference",
                "message": str(e),
            })

    # 5) 境界フォーカス: border.focus vs bg.page
    _check_contrast(
        tokens, "border.focus", "bg.page", MIN_BORDER_FOCUS_CONTRAST,
        "border_focus_contrast_too_low", definition, errors,
    )

    if errors:
        raise ThemeValidationError(errors)
    return parsed


def _check_contrast(
    tokens: dict[str, str],
    fg_key: str,
    bg_key: str,
    min_ratio: float,
    code: str,
    definition: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    fg = tokens.get(fg_key)
    bg = tokens.get(bg_key)
    if not fg or not bg:
        errors.append({
            "field": f"semanticTokens.{fg_key}",
            "code": "missing_token",
            "message": f"semanticTokens.{fg_key} と semanticTokens.{bg_key} は必須です",
        })
        return
    try:
        fg_hex = resolve_color(fg, definition)
        bg_hex = resolve_color(bg, definition)
    except ValueError as e:
        errors.append({
            "field": f"semanticTokens.{fg_key}",
            "code": "unresolved_token_reference",
            "message": str(e),
        })
        return
    ratio = contrast_ratio(fg_hex, bg_hex)
    if ratio < min_ratio:
        errors.append({
            "field": f"semanticTokens.{fg_key}",
            "code": code,
            "message": f"{fg_key} と {bg_key} のコントラスト比は {min_ratio}:1 以上が必要です(現在 {ratio:.2f}:1)",
        })
