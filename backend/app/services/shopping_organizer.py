"""既存の買い物リストをAIで整理するサービス。

同じ/類似食材を統合し、カテゴリを標準化する。既存の ShoppingItem 行を削除し、
Ollama の応答を元に新しい ShoppingItem 行を挿入する。
Pantry在庫チェックは整理後の名前で再実行する。
"""

import json
import logging
import re
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.pantry import get_available_pantry_names
from app.db.models.shopping import ShoppingItem, ShoppingRequest
from app.services.llm_client import OllamaClient, OllamaInvalidJSONError

logger = logging.getLogger(__name__)


STANDARD_CATEGORIES = ("野菜", "肉類", "魚介類", "卵・乳製品", "穀類", "調味料", "その他")

# 複合名（「塩、パセリ、マヨネーズ」「刻みネギ・ごま」等）を分割するセパレータ
_COMPOUND_SPLIT = re.compile(r"[、・]|または")


def _split_compound(name: str) -> list[str]:
    """複合名を分割。ただし括弧内のセパレータでは分割しない。

    例: 'サーモン（刺身用またはスモークサーモン）' → ['サーモン（刺身用またはスモークサーモン）']
    例: '塩、パセリ' → ['塩', 'パセリ']
    例: '刻みネギ・ごま' → ['刻みネギ', 'ごま']
    """
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    i = 0
    while i < len(name):
        ch = name[i]
        if ch in "（(":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch in "）)":
            depth = max(0, depth - 1)
            buf.append(ch)
            i += 1
            continue
        if depth == 0:
            # セパレータ判定（「または」は2文字、その他は1文字）
            if name.startswith("または", i):
                if buf:
                    parts.append("".join(buf).strip())
                    buf = []
                i += 3
                continue
            if ch in "、・":
                if buf:
                    parts.append("".join(buf).strip())
                    buf = []
                i += 1
                continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]
# 括弧修飾（有塩）（小ぶり）（皮なし）（後のせ用）等を削除
_PAREN_QUALIFIER = re.compile(r"[（(][^）)]*[）)]")
# 括弧内が数量を示唆するかを判定
_QUANTITY_HINT = re.compile(r"[0-9０-９]|適量|少々|大さじ|小さじ|カップ|[gkml]|cc|kg")
# 名前末尾に直書きされた数量表現を削除するための正規表現
# (1) 各?(大さじ|小さじ|カップ) + 数字  例: 大さじ1, 小さじ1/2, 各大さじ2
# (2) 各?数字 + 単位                   例: 3個, 1/2本, 100g, 1〜2本
# (3) 数字のみ                        例: 10 (末尾の残り)
# (4) 副詞的な数量表現                  例: 適量, 少々, お好み, 適宜, あれば
_TRAILING_QUANTITY = re.compile(
    r"\s*(?:"
    r"各?(?:大さじ|小さじ|カップ)\s*[0-9０-９.／/〜\-]+(?:[0-9０-９.／/〜\-]*)?"
    r"|"
    r"各?[0-9０-９.／/〜\-]+\s*(?:個|枚|本|束|パック|袋|切れ|片|丁|尾|缶|粒|cc|ml|L|g|kg|合|さじ|カップ)"
    r"|"
    r"[0-9０-９.／/〜\-]+"
    r"|"
    r"適量|少々|お好み|適宜|あれば|ふたつまみ|ひとつまみ|好きなだけ|少量"
    r")\s*$"
)
# 文字列から数量パターンのみ抽出（レシピ名を除いた数量のみ取り出す用）
_QTY_PATTERN = re.compile(
    r"各?(?:大さじ|小さじ|カップ)\s*[0-9０-９.／/〜\-]+"
    r"|各?[0-9０-９.／/〜\-]+\s*(?:個|枚|本|束|パック|袋|切れ|片|丁|尾|缶|粒|cc|ml|L|g|kg|合)"
    r"|適量|少々|お好み|適宜|あれば|ふたつまみ|ひとつまみ|好きなだけ|少量"
)

# 同義語を標準名に正規化（LLMに渡す前に適用して exact match でマージさせる）
_SYNONYMS: dict[str, str] = {
    # 胡椒類
    "塩胡椒": "胡椒",
    "塩コショウ": "胡椒",
    "こしょう": "胡椒",
    "コショウ": "胡椒",
    "黒胡椒": "胡椒",
    "黒こしょう": "胡椒",
    "黒コショウ": "胡椒",
    "ブラックペッパー": "胡椒",
    "粗挽き黒こしょう": "胡椒",
    "粗挽き黒コショウ": "胡椒",
    "粗挽き黒胡椒": "胡椒",
    # にんにく系
    "おろしにんにく": "にんにく",
    "ニンニク": "にんにく",
    "ニンニクすりおろし": "にんにく",
    "にんにくすりおろし": "にんにく",
    "すりおろしにんにく": "にんにく",
    "すりおろしニンニク": "にんにく",
    # しょうが系
    "おろししょうが": "しょうが",
    "生姜": "しょうが",
    "すりおろし生姜": "しょうが",
    "すりおろししょうが": "しょうが",
    # 玉ねぎ系
    "新玉ねぎ": "玉ねぎ",
    "新玉": "玉ねぎ",
    "新たま": "玉ねぎ",
    "新たまねぎ": "玉ねぎ",
    "新玉葱": "玉ねぎ",
    "玉葱": "玉ねぎ",
    "たまねぎ": "玉ねぎ",
    # ねぎ系（青ねぎ/万能ねぎ/小ねぎは全て薬味用の細ねぎ）
    "ネギ": "ねぎ",
    "青ネギ": "ねぎ",
    "青ねぎ": "ねぎ",
    "万能ねぎ": "ねぎ",
    "万能ネギ": "ねぎ",
    "刻みネギ": "ねぎ",
    "刻みねぎ": "ねぎ",
    "小ねぎ": "ねぎ",
    "小ネギ": "ねぎ",
    "細ねぎ": "ねぎ",
    "細ネギ": "ねぎ",
    "小口切りネギ": "ねぎ",
    # パセリ系
    "粉末パセリ": "パセリ",
    "ドライパセリ": "パセリ",
    # 魚介類（表記ゆれ）
    "びんちょう鮪": "まぐろ",
    "ビンチョウマグロ": "まぐろ",
    "マグロ": "まぐろ",
    "鮪": "まぐろ",
    "タラの切り身": "タラ",
    "鱈": "タラ",
    "たら": "タラ",
    "黒アワビ": "アワビ",
    # 醤油系
    "しょう油": "醤油",
    "しょうゆ": "醤油",
    "ショウユ": "醤油",
    # 酒系（紹興酒は別の特定酒なので残す）
    "日本酒": "酒",
    # 酢系（黒酢は別カテゴリでも本酢として統合）
    "穀物酢": "酢",
    # 出汁系
    "鰹節": "かつお節",
    "削りおかか": "かつお節",
    "おかか": "かつお節",
    "削り節": "かつお節",
    # ごま系
    "白すりごま": "ごま",
    "すりごま": "ごま",
    "白ごま": "ごま",
    "いりごま": "ごま",
    # チーズ系（別種は残す）
    "とろけるチーズ": "とろけるチーズ",
}

# 正規化後の名前ごとにカテゴリを強制（LLM の判定より優先）
_CATEGORY_OVERRIDE: dict[str, str] = {
    # 魚介類
    "まぐろ": "魚介類",
    "タラ": "魚介類",
    "アワビ": "魚介類",
    "サーモン": "魚介類",
    "エビ": "魚介類",
    "びんちょう鮪": "魚介類",
    # 調味料
    "胡椒": "調味料",
    "塩": "調味料",
    "にんにく": "調味料",
    "しょうが": "調味料",
    "マヨネーズ": "調味料",
    "醤油": "調味料",
    "酒": "調味料",
    "紹興酒": "調味料",
    "酢": "調味料",
    "みりん": "調味料",
    "砂糖": "調味料",
    "ごま油": "調味料",
    "オリーブオイル": "調味料",
    "サラダ油": "調味料",
    "オイスターソース": "調味料",
    "ポン酢": "調味料",
    "和風だし": "調味料",
    "鶏がらスープの素": "調味料",
    "梅肉ソース": "調味料",
    "牡蠣だし醤油": "調味料",
    "本つゆ": "調味料",
    "本葛粉": "調味料",
    "片栗粉": "調味料",
    "薄力粉": "調味料",
    "薄力粉または片栗粉": "調味料",
    "味の素": "調味料",
    "味覇": "調味料",
    "レモン汁": "調味料",
    "ごま": "調味料",
    "かつお節": "調味料",
    # 野菜
    "パセリ": "野菜",
    "玉ねぎ": "野菜",
    "ねぎ": "野菜",
    "青ネギ": "野菜",
    "万能ねぎ": "野菜",
    "刻みネギ": "野菜",
    "サラダ菜": "野菜",
    "パプリカ": "野菜",
}

# 買い物リストに含めるべきでない食材（既存の shopping_list_generator にもあるが、
# 名前の表記ゆれでスルーされたもの（例: "水（レンジ蒸し用）"）を organize 時に除外）
_SKIP_NAMES: set[str] = {"水", "氷", "お湯", "熱湯", "ぬるま湯", "冷水", "キユーピー"}

SYSTEM_PROMPT = (
    "あなたは日本の家庭料理に詳しい買い物リスト整理の専門家です。"
    "与えられた食材リストを同じ/類似食材ごとに積極的に統合し、指定カテゴリに分類してください。"
    "必ず指定された JSON スキーマのみで回答し、説明文やコードブロックは出力しないでください。"
)


class ShoppingRequestNotFoundError(Exception):
    pass


class OrganizeValidationError(Exception):
    pass


def _clean_name(name: str) -> str:
    """食材名から括弧修飾・末尾の数量を除去し、統合用のキーを作る。"""
    cleaned, _ = _clean_name_with_qty(name)
    return cleaned


def _clean_name_with_qty(name: str) -> tuple[str, list[str]]:
    """名前から数量を抜き出して (cleaned_name, extracted_quantities) を返す。

    例:
        '鶏むね肉（皮なし）1枚（250g）' → ('鶏むね肉', ['1枚', '250g'])
        'オリーブオイル（炒め用）適量' → ('オリーブオイル', ['適量'])
    """
    extracted: list[str] = []

    def _paren_fn(m: re.Match) -> str:
        inner = m.group(0)[1:-1].strip()
        if _QUANTITY_HINT.search(inner):
            extracted.append(inner)
        return ""

    n = _PAREN_QUALIFIER.sub(_paren_fn, name)
    # 末尾の数量を繰り返し除去
    prev = None
    while prev != n:
        prev = n
        m = _TRAILING_QUANTITY.search(n)
        if m and m.end() == len(n):
            q = m.group(0).strip()
            if q:
                extracted.append(q)
            n = n[: m.start()].rstrip()
    cleaned = n.strip()
    # 同義語を正規化
    cleaned = _SYNONYMS.get(cleaned, cleaned)
    return cleaned, extracted


def _preprocess_items(items: list[ShoppingItem]) -> list[dict]:
    """LLM に渡す前に決定的な前処理でノイズを減らす:
    - 複合名（「塩、パセリ」等）を分割して別アイテム化
    - 名前から括弧修飾・末尾数量を除去
    - 同一クリーン名を exact match でマージ
    戻り値: [{"name", "quantities": [...], "category", "is_excluded"}]
    """
    groups: dict[str, dict] = {}
    for it in items:
        raw_name = it.item_name or ""
        raw_qty = it.quantity or ""
        parts = _split_compound(raw_name)
        if not parts:
            parts = [raw_name]
        for part in parts:
            cleaned, extra_qtys = _clean_name_with_qty(part)
            if not cleaned:
                continue
            # スキップ対象（水/氷/ブランド名など）は除外
            if cleaned in _SKIP_NAMES:
                continue
            key = cleaned
            # カテゴリは override を優先、なければ元のカテゴリ
            default_cat = _CATEGORY_OVERRIDE.get(cleaned, it.category or "その他")
            if key not in groups:
                groups[key] = {
                    "name": cleaned,
                    "quantities": [],
                    "category": default_cat,
                    "is_excluded": True,  # 全員 excluded のときのみ true
                }
            g = groups[key]
            if raw_qty:
                g["quantities"].append(raw_qty)
            # 名前に埋め込まれていた数量も救出（「1枚」「250g」等）。
            # ただし「適量」「少々」など数値を含まない曖昧表現は除外（情報を追加せず、
            # LLM が具体値を捨てて曖昧語を採用してしまう副作用を避ける）。
            for q in extra_qtys:
                if re.search(r"[0-9０-９]", q):
                    g["quantities"].append(q)
            if not it.is_excluded:
                g["is_excluded"] = False
    return list(groups.values())


_VAGUE_WORDS = {"適量", "少々", "お好み", "適宜", "あれば", "ふたつまみ", "ひとつまみ", "好きなだけ", "少量"}


def _is_vague(q: str) -> bool:
    """数量表現が曖昧（数値を含まない）か判定。"""
    q = q.strip()
    return not re.search(r"[0-9０-９]", q)


def _collapse_slash_quantity(q: str) -> str:
    """' / ' で区切られた複数数量を統合する。

    - 具体値（数字を含む）があれば、それらを「、」連結
    - 全て曖昧語なら最初のものだけ残す
    """
    parts = [p.strip() for p in q.split(" / ") if p.strip()]
    parts = list(dict.fromkeys(parts))  # 重複削除
    if not parts:
        return ""
    specific = [p for p in parts if not _is_vague(p)]
    if specific:
        return "、".join(specific)
    return parts[0]


_TOTAL_PREFIX = re.compile(r"^\s*合計[ 　]*")


def _clean_output_quantity(q: str | None) -> str | None:
    """LLM出力数量を整える: '合計 ' プレフィックス除去、曖昧語の冗長重複を整理。"""
    if not q:
        return q
    cleaned = _TOTAL_PREFIX.sub("", q).strip()
    # 「、」「,」「 / 」区切りのトークンを取り出し
    tokens = [t.strip() for t in re.split(r"[、,]|\s/\s", cleaned) if t.strip()]
    if not tokens:
        return cleaned or None
    # 重複削除（順序保持）
    tokens = list(dict.fromkeys(tokens))
    specific = [t for t in tokens if not _is_vague(t)]
    if specific:
        # 具体値がある場合は曖昧語を捨てる（数値情報を優先）
        return "、".join(specific)
    # 全て曖昧語なら1つだけ残す（情報量はどれも同じ）
    return tokens[0]


def _merge_same_name(items: list[dict]) -> list[dict]:
    """LLM が返した結果に同名エントリが複数あれば合算する。
    数量は具体値（数字を含む）があればそちらを優先し、曖昧語（適量・少々など）は切り捨てる。
    """
    merged: dict[str, dict] = {}
    for it in items:
        key = it["item_name"]
        if key not in merged:
            merged[key] = dict(it)
            continue
        existing = merged[key]
        qa = (existing.get("quantity") or "").strip()
        qb = (it.get("quantity") or "").strip()
        # 数量の合併: 具体値 > 曖昧語
        va, vb = _is_vague(qa), _is_vague(qb)
        if qa and qb:
            if va and not vb:
                combined = qb  # qb が具体的
            elif vb and not va:
                combined = qa  # qa が具体的
            elif va and vb:
                combined = qa  # 両方曖昧 → 最初のまま
            else:
                combined = qa if qa == qb else f"{qa}、{qb}"
        else:
            combined = qa or qb or None
        if combined and len(combined) > 200:
            combined = combined[:197] + "…"
        existing["quantity"] = combined
        # is_excluded は全エントリ excluded のときのみ true
        existing["is_excluded"] = bool(existing.get("is_excluded")) and bool(it.get("is_excluded"))
    return list(merged.values())


def _simplify_quantity_string(raw: str) -> str:
    """「（レシピ名 大さじ2 + レシピ名 適量 + ...）」形式から数量のみ抽出する。

    元のリストはレシピ名が混在していてLLMを混乱させるため、数量パターンのみ
    拾って列挙する。数量が一つも見つからなければ元の文字列を返す。
    """
    found = _QTY_PATTERN.findall(raw)
    if not found:
        return raw
    # 具体値（数字を含む）を優先し、曖昧表現は末尾にまとめる
    specific = [q for q in found if re.search(r"[0-9０-９]", q)]
    vague = [q for q in found if not re.search(r"[0-9０-９]", q)]
    combined = specific + list(dict.fromkeys(vague))
    return "、".join(combined)


def _build_user_prompt(items: list[ShoppingItem]) -> str:
    preprocessed = _preprocess_items(items)
    lines = []
    for i, g in enumerate(preprocessed, start=1):
        # 数量は重複削除、複数あれば簡潔化してからLLMに渡す
        simplified = [_simplify_quantity_string(q) for q in g["quantities"]]
        unique_q = list(dict.fromkeys(q for q in simplified if q))
        qty_text = " / ".join(unique_q) if unique_q else ""
        if len(qty_text) > 180:
            qty_text = qty_text[:177] + "…"
        excluded = "在庫あり" if g["is_excluded"] else "要購入"
        lines.append(f"{i}. {g['name']} | {qty_text} | {g['category']} | {excluded}")
    item_block = "\n".join(lines)

    example = {
        "items": [
            {"name": "玉ねぎ", "quantity": "3個", "category": "野菜", "is_excluded": False},
            {"name": "胡椒", "quantity": "少々", "category": "調味料", "is_excluded": False},
        ]
    }

    return (
        "【整理前のリスト】 形式: 連番. name | quantity | category | status\n"
        f"{item_block}\n\n"
        "【必ず統合する類似食材の例】\n"
        "- 新玉ねぎ / 新たまねぎ / 玉ねぎ / 新玉 → 「玉ねぎ」\n"
        "- 塩コショウ / 塩胡椒 / ブラックペッパー / 黒胡椒 / 黒こしょう / 粗挽き黒こしょう / 胡椒 → 「胡椒」\n"
        "- ニンニク / にんにく / おろしにんにく / すりおろしニンニク → 「にんにく」\n"
        "- しょうが / 生姜 / おろししょうが / すりおろし生姜 → 「しょうが」\n"
        "- オリーブオイル（炒め用）/ オリーブオイル → 「オリーブオイル」\n"
        "- バター（有塩）/ バター → 「バター」\n"
        "- 粉チーズ（後のせ用）/ 粉チーズ → 「粉チーズ」\n"
        "- 醤油 / しょうゆ / しょう油 → 「醤油」\n"
        "- 酒 / 日本酒 → 「酒」（紹興酒は別として残す）\n"
        "- 鰹節 / かつお節 / 削りおかか / おかか → 「かつお節」\n"
        "- 白すりごま / すりごま / 白ごま / ごま → 「ごま」\n"
        "- 薄力粉または片栗粉 → 「薄力粉」\n"
        "- ネギ / 青ネギ / 刻みネギ / 万能ねぎ / 小口切りネギ / 細ねぎ → 「ねぎ」\n"
        "- サラダ菜 / レタス → それぞれ別（混同しない）\n"
        "- 鶏もも肉 / 鶏むね肉 / 鶏ささみ → 部位ごとに別（統合しない）\n"
        "- スライスチーズ / とろけるチーズ / 粉チーズ / ベビーチーズ → それぞれ別（混同しない）\n\n"
        "【整理ルール】\n"
        "- 同じ食材または明らかな類似食材を1つに統合する（上記の例を参考に積極的に統合）\n"
        "- 統合時の数量は合計できれば合計（例: '2個 + 3個' → '5個'）、単位が混在する場合は簡潔に併記（例: '1束、150g'）\n"
        "- 数量に「合計 」プレフィックスは付けない。具体値があるときは曖昧語（適量・少々・適宜・あれば 等）は省く\n"
        "- レシピ名を含む長い数量注釈は出力に含めない。量の本質のみを残す\n"
        "- カテゴリは必ず次のいずれか: 野菜 / 肉類 / 魚介類 / 卵・乳製品 / 穀類 / 調味料 / その他\n"
        "- 砂糖・塩・醤油・味噌・酢・油・みりん・だし・スパイス類・スープの素・市販ソースは「調味料」\n"
        "- 梅肉ソース・鶏がらスープの素・牡蠣だし醤油・本つゆ・味の素・味覇 など → 「調味料」\n"
        "- きゅうり・トマト・玉ねぎ・ねぎ・きのこ類・葉物などは「野菜」\n"
        "- is_excluded は元の全エントリが「在庫あり」のとき true、1つでも「要購入」があれば false\n"
        "- 元のリストにない食材を追加してはならない\n\n"
        "【出力形式】下記スキーマの JSON のみを出力。\n"
        f"{json.dumps(example, ensure_ascii=False)}\n"
    )


def _validate_items(raw: dict, known_names: set[str] | None = None) -> list[dict]:
    if not isinstance(raw, dict):
        raise OrganizeValidationError("レスポンスが辞書ではありません")
    items = raw.get("items")
    if not isinstance(items, list) or not items:
        raise OrganizeValidationError("items フィールドが空または不正です")

    out = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()[:100]
        # LLMがカテゴリ名そのものを食材として出力する場合があるため除外
        if name in STANDARD_CATEGORIES:
            continue
        # LLM出力にも同義語正規化を適用（大元のキーで統合）
        name = _SYNONYMS.get(name, name)
        # スキップ対象は除外
        if name in _SKIP_NAMES:
            continue
        # ホワイトリスト検証（LLM幻覚で元にない食材が入ることを防ぐ）
        if known_names is not None and name not in known_names:
            continue
        qty = entry.get("quantity")
        if qty is not None and not isinstance(qty, str):
            qty = str(qty)
        if qty is not None:
            qty = qty.strip()[:200] or None
            # LLM が入力の " / " 区切りをそのまま echo することがあるので畳む
            if qty and " / " in qty:
                qty = _collapse_slash_quantity(qty)
            qty = _clean_output_quantity(qty)

        category = entry.get("category")
        if category not in STANDARD_CATEGORIES:
            category = "その他"
        # 既知食材はカテゴリを強制上書き
        if name in _CATEGORY_OVERRIDE:
            category = _CATEGORY_OVERRIDE[name]

        is_excluded = bool(entry.get("is_excluded", False))

        out.append({
            "item_name": name,
            "quantity": qty,
            "category": category,
            "is_excluded": is_excluded,
        })

    if not out:
        raise OrganizeValidationError("有効な items が1件もありません")
    return out


async def organize_shopping_request(
    db: AsyncSession,
    user_id: uuid.UUID,
    request_id: uuid.UUID,
    client: OllamaClient | None = None,
) -> ShoppingRequest:
    """指定の ShoppingRequest をAIで整理する。

    - request の所有者チェック (senior_user_id == user_id) を行う
    - 既存の ShoppingItem を全削除し、AI応答ベースで再生成する
    - pantry 在庫を再チェックして is_excluded を更新する
    """
    result = await db.execute(
        select(ShoppingRequest)
        .where(ShoppingRequest.id == request_id)
        .options(selectinload(ShoppingRequest.items))
    )
    request = result.scalar_one_or_none()
    if not request or request.senior_user_id != user_id:
        raise ShoppingRequestNotFoundError()

    original_items = list(request.items)
    if not original_items:
        return request

    # 前処理で決定的に重複統合し、整理前のホワイトリストを作る（LLM幻覚の防止）
    preprocessed = _preprocess_items(original_items)
    known_names = {g["name"] for g in preprocessed}

    user_prompt = _build_user_prompt(original_items)

    client = client or OllamaClient()
    # 買い物リストは量子数が多いため context 窓を広げる。
    # 温度は低めにして出力を安定させる（毎回異なる結果になるのを防ぐ）。
    raw = await client.chat_json(SYSTEM_PROMPT, user_prompt, temperature=0.1, num_ctx=12288)
    organized = _validate_items(raw, known_names=known_names)
    # LLM が同名の複数行を返すことがあるので post-merge
    organized = _merge_same_name(organized)

    # LLM が一部食材を出力から落とす場合があるので、失われた食材を復元する。
    # 前処理結果から漏れたものを最低限の数量で追加（情報の欠落を防ぐ）。
    output_names = {it["item_name"] for it in organized}
    by_name = {g["name"]: g for g in preprocessed}
    for name in known_names - output_names:
        g = by_name[name]
        # 数量を簡潔化して結合
        simplified = [_simplify_quantity_string(q) for q in g["quantities"]]
        unique_q = list(dict.fromkeys(q for q in simplified if q))
        qty = _clean_output_quantity("、".join(unique_q)) if unique_q else None
        category = _CATEGORY_OVERRIDE.get(name, g["category"])
        if category not in STANDARD_CATEGORIES:
            category = "その他"
        organized.append({
            "item_name": name,
            "quantity": qty,
            "category": category,
            "is_excluded": bool(g["is_excluded"]),
        })
        logger.info("organize: 復元した食材 %s (LLM出力から欠落)", name)

    # Pantryチェック用の在庫名（整理後の名前で再判定する）
    pantry_names = await get_available_pantry_names(db, user_id)

    # 既存アイテムを全削除
    await db.execute(
        delete(ShoppingItem).where(ShoppingItem.shopping_request_id == request.id)
    )
    await db.flush()

    # 新アイテム挿入
    for entry in organized:
        in_pantry = entry["item_name"] in pantry_names
        item = ShoppingItem(
            shopping_request_id=request.id,
            item_name=entry["item_name"],
            category=entry["category"],
            quantity=entry["quantity"],
            # AIが「在庫あり」と判断した or 名前がpantryに一致 → 除外
            is_excluded=bool(entry["is_excluded"]) or in_pantry,
            status="pending",
        )
        db.add(item)

    await db.flush()

    # 再ロードして返す
    result = await db.execute(
        select(ShoppingRequest)
        .where(ShoppingRequest.id == request.id)
        .options(selectinload(ShoppingRequest.items))
    )
    return result.scalar_one()
