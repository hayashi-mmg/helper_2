from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.crud.menu import (
    build_menu_response,
    clear_weekly_menu,
    copy_weekly_menu,
    get_weekly_menu,
    upsert_weekly_menu,
)
from app.db.models.user import User
from app.schemas.menu import WeeklyMenuClear, WeeklyMenuCopy, WeeklyMenuUpdate
from app.schemas.menu_suggestion import MenuSuggestionRequest, WeeklyMenuSuggestionResponse
from app.services.llm_client import (
    OllamaInvalidJSONError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.services.menu_suggester import (
    RecipeCatalogEmptyError,
    SuggestionValidationError,
    suggest_weekly_menu,
)

router = APIRouter(prefix="/menus", tags=["献立"])


def _normalize_week_start(d: date) -> date:
    """指定日を含む週の月曜日を返す。"""
    return d - timedelta(days=d.weekday())


@router.get("/week")
async def get_week_menu(
    date_param: date | None = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week_start = _normalize_week_start(date_param or date.today())
    menu = await get_weekly_menu(db, current_user.id, week_start)
    return await build_menu_response(menu, week_start)


@router.put("/week")
async def update_week_menu(
    data: WeeklyMenuUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week_start = _normalize_week_start(data.week_start)
    menus_dict = {
        day: {"breakfast": [r.model_dump() for r in slot.breakfast], "dinner": [r.model_dump() for r in slot.dinner]}
        for day, slot in data.menus.items()
    }
    menu = await upsert_weekly_menu(db, current_user.id, week_start, menus_dict)
    return await build_menu_response(menu, week_start)


@router.post("/week/copy")
async def copy_week_menu(
    data: WeeklyMenuCopy,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source_week = _normalize_week_start(data.source_week)
    target_week = _normalize_week_start(data.target_week)

    if source_week == target_week:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="コピー元とコピー先が同じ週です")

    menu = await copy_weekly_menu(db, current_user.id, source_week, target_week)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="コピー元の献立が見つかりません")

    return await build_menu_response(menu, target_week)


@router.post("/week/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_week_menu(
    data: WeeklyMenuClear,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week_start = _normalize_week_start(data.week_start)
    await clear_weekly_menu(db, current_user.id, week_start)


@router.post("/suggest", response_model=WeeklyMenuSuggestionResponse)
async def suggest_week_menu(
    data: MenuSuggestionRequest,
    current_user: User = Depends(require_role("senior")),
    db: AsyncSession = Depends(get_db),
):
    """Ollama による1週間分の献立提案（利用者本人のみ）。

    提案結果は DB 保存せず返却する。利用者が画面で確認後、既存の
    ``PUT /menus/week`` で適用する。
    """
    normalized_request = MenuSuggestionRequest(
        week_start=_normalize_week_start(data.week_start),
        dietary_restrictions=data.dietary_restrictions,
        avoid_ingredients=data.avoid_ingredients,
        notes=data.notes,
    )
    try:
        return await suggest_weekly_menu(db, current_user.id, normalized_request)
    except RecipeCatalogEmptyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="レシピが登録されていません。先にレシピを登録してください",
        )
    except OllamaUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="献立提案サービスに接続できません",
        )
    except OllamaTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="提案に時間がかかりすぎました。もう一度お試しください",
        )
    except (OllamaInvalidJSONError, SuggestionValidationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="提案の解析に失敗しました。もう一度お試しください",
        )
