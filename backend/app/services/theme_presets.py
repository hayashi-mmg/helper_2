"""プリセットテーマ定義。

マイグレーションシードとフロントエンドフォールバックの真実の源として使用する。
仕様: docs/theme_system_specification.md §4
"""
from typing import Any


STANDARD: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "standard",
    "name": "スタンダード",
    "description": "既定テーマ。青系ブランドで視認性と汎用性を両立。",
    "colors": {
        "brand": {
            "50": "#e3f2fd", "100": "#bbdefb", "200": "#90caf9", "300": "#64b5f6",
            "400": "#42a5f5", "500": "#1976d2", "600": "#1565c0", "700": "#0d47a1",
            "800": "#0b3d91", "900": "#08306b",
        },
        "semantic": {
            "success": "#2e7d32",
            "danger": "#c62828",
            "warn": "#e65100",
            "info": "#0277bd",
        },
        "neutral": {
            "50": "#fafafa", "100": "#f5f5f5", "200": "#eeeeee", "300": "#e0e0e0",
            "400": "#bdbdbd", "500": "#9e9e9e", "600": "#616161", "700": "#424242",
            "800": "#212121", "900": "#000000",
        },
    },
    "semanticTokens": {
        "bg.page": "{colors.neutral.50}",
        "bg.card": "#ffffff",
        "bg.subtle": "{colors.neutral.100}",
        "text.primary": "{colors.neutral.800}",
        "text.secondary": "{colors.neutral.700}",
        "text.onBrand": "#ffffff",
        "border.default": "{colors.neutral.300}",
        "border.focus": "{colors.brand.700}",
    },
    "fonts": {
        "body": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "heading": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "baseSizePx": 18,
    },
    "radii": {"sm": "0.25rem", "md": "0.5rem", "lg": "0.75rem", "full": "9999px"},
    "density": "comfortable",
    "meta": {"tags": ["builtin", "default"]},
}


HIGH_CONTRAST: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "high-contrast",
    "name": "ハイコントラスト",
    "description": "弱視・高齢者向け。黒白主体の強コントラスト。",
    "colors": {
        "brand": {
            "50": "#f5f5f5", "100": "#e0e0e0", "200": "#bdbdbd", "300": "#9e9e9e",
            "400": "#616161", "500": "#000000", "600": "#000000", "700": "#000000",
            "800": "#000000", "900": "#000000",
        },
        "semantic": {
            "success": "#0d4d10",
            "danger": "#8b0000",
            "warn": "#8b3900",
            "info": "#003d6b",
        },
        "neutral": {
            "50": "#ffffff", "100": "#f5f5f5", "200": "#eeeeee", "300": "#bdbdbd",
            "400": "#757575", "500": "#424242", "600": "#212121", "700": "#121212",
            "800": "#000000", "900": "#000000",
        },
    },
    "semanticTokens": {
        "bg.page": "#ffffff",
        "bg.card": "#ffffff",
        "bg.subtle": "{colors.neutral.100}",
        "text.primary": "#000000",
        "text.secondary": "{colors.neutral.600}",
        "text.onBrand": "#ffffff",
        "border.default": "{colors.neutral.500}",
        "border.focus": "#000000",
    },
    "fonts": {
        "body": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "heading": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "baseSizePx": 20,
    },
    "radii": {"sm": "0.125rem", "md": "0.25rem", "lg": "0.5rem", "full": "9999px"},
    "density": "spacious",
    "meta": {"tags": ["builtin", "accessibility"]},
}


WARM: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "warm",
    "name": "温もり",
    "description": "居宅介護の温かみを表現する橙系テーマ。",
    "colors": {
        "brand": {
            "50": "#fff3e0", "100": "#ffe0b2", "200": "#ffcc80", "300": "#ffb74d",
            "400": "#ffa726", "500": "#b84d00", "600": "#a14300", "700": "#8a3a00",
            "800": "#732f00", "900": "#5a2500",
        },
        "semantic": {
            "success": "#2e7d32",
            "danger": "#b71c1c",
            "warn": "#b84d00",
            "info": "#01579b",
        },
        "neutral": {
            "50": "#fffaf4", "100": "#fdf3e5", "200": "#f3e3cc", "300": "#e5d0b0",
            "400": "#b89773", "500": "#7a624a", "600": "#5e4a36", "700": "#3f3322",
            "800": "#2b2116", "900": "#1a140c",
        },
    },
    "semanticTokens": {
        "bg.page": "{colors.neutral.50}",
        "bg.card": "#ffffff",
        "bg.subtle": "{colors.neutral.100}",
        "text.primary": "{colors.neutral.800}",
        "text.secondary": "{colors.neutral.700}",
        "text.onBrand": "#ffffff",
        "border.default": "{colors.neutral.300}",
        "border.focus": "{colors.brand.700}",
    },
    "fonts": {
        "body": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "heading": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "baseSizePx": 18,
    },
    "radii": {"sm": "0.375rem", "md": "0.75rem", "lg": "1rem", "full": "9999px"},
    "density": "comfortable",
    "meta": {"tags": ["builtin", "warm"]},
}


CALM: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "calm",
    "name": "おだやか",
    "description": "長時間閲覧でも疲れにくい低彩度の緑系テーマ。",
    "colors": {
        "brand": {
            "50": "#eef5ef", "100": "#d3e4d5", "200": "#b5d1b8", "300": "#97be9b",
            "400": "#7fae83", "500": "#356b3a", "600": "#2d5c32", "700": "#254c28",
            "800": "#1c3c1f", "900": "#132c15",
        },
        "semantic": {
            "success": "#2e7d32",
            "danger": "#c62828",
            "warn": "#b84d00",
            "info": "#0277bd",
        },
        "neutral": {
            "50": "#f7f8f7", "100": "#eceeec", "200": "#d6dbd7", "300": "#b8c0b9",
            "400": "#8a948b", "500": "#5a655c", "600": "#414a42", "700": "#2e342f",
            "800": "#1d211e", "900": "#0f110f",
        },
    },
    "semanticTokens": {
        "bg.page": "{colors.neutral.50}",
        "bg.card": "#ffffff",
        "bg.subtle": "{colors.neutral.100}",
        "text.primary": "{colors.neutral.800}",
        "text.secondary": "{colors.neutral.700}",
        "text.onBrand": "#ffffff",
        "border.default": "{colors.neutral.300}",
        "border.focus": "{colors.brand.700}",
    },
    "fonts": {
        "body": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "heading": "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        "baseSizePx": 18,
    },
    "radii": {"sm": "0.25rem", "md": "0.5rem", "lg": "0.75rem", "full": "9999px"},
    "density": "spacious",
    "meta": {"tags": ["builtin", "calm"]},
}


BUILTIN_PRESETS: list[tuple[str, str, str | None, dict[str, Any]]] = [
    ("standard", STANDARD["name"], STANDARD["description"], STANDARD),
    ("high-contrast", HIGH_CONTRAST["name"], HIGH_CONTRAST["description"], HIGH_CONTRAST),
    ("warm", WARM["name"], WARM["description"], WARM),
    ("calm", CALM["name"], CALM["description"], CALM),
]
"""(theme_key, name, description, definition) のタプル一覧。マイグレーションシードで使用。"""
