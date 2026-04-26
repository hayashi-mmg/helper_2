import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.shopping import (
    create_shopping_request,
    get_shopping_request_by_id,
    get_shopping_requests,
    update_shopping_item,
)
from app.db.models.shopping import ShoppingItem
from app.db.models.user import User
from app.schemas.shopping import (
    ExcludeRequest,
    ExcludeResponse,
    GenerateFromMenuRequest,
    GenerateFromMenuResponse,
    GenerateSummary,
    GeneratedItemResponse,
    ShoppingItemResponse,
    ShoppingItemUpdate,
    ShoppingRequestCreate,
    ShoppingRequestResponse,
)
from app.services.llm_client import (
    OllamaInvalidJSONError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.services.shopping_list_generator import generate_shopping_list_from_menu
from app.services.shopping_organizer import (
    OrganizeValidationError,
    ShoppingRequestNotFoundError,
    organize_shopping_request,
)

router = APIRouter(prefix="/shopping", tags=["買い物管理"])


@router.get("/requests", response_model=list[ShoppingRequestResponse])
async def list_shopping_requests(
    request_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requests = await get_shopping_requests(db, current_user.id, request_status)
    return [
        ShoppingRequestResponse(
            id=str(r.id), senior_user_id=str(r.senior_user_id),
            helper_user_id=str(r.helper_user_id),
            request_date=r.request_date, status=r.status, notes=r.notes,
            items=[
                ShoppingItemResponse(
                    id=str(item.id), item_name=item.item_name, category=item.category,
                    quantity=item.quantity, memo=item.memo, status=item.status,
                    created_at=item.created_at,
                )
                for item in r.items
            ],
            created_at=r.created_at,
        )
        for r in requests
    ]


@router.post("/requests", response_model=ShoppingRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_shopping_request_endpoint(
    data: ShoppingRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    request_data = {
        "senior_user_id": uuid.UUID(data.senior_user_id),
        "helper_user_id": current_user.id,
        "request_date": data.request_date,
        "notes": data.notes,
    }
    items_data = [item.model_dump() for item in data.items]

    request = await create_shopping_request(db, request_data, items_data)

    # Reload with items
    request = await get_shopping_request_by_id(db, request.id)

    return ShoppingRequestResponse(
        id=str(request.id), senior_user_id=str(request.senior_user_id),
        helper_user_id=str(request.helper_user_id),
        request_date=request.request_date, status=request.status, notes=request.notes,
        items=[
            ShoppingItemResponse(
                id=str(item.id), item_name=item.item_name, category=item.category,
                quantity=item.quantity, memo=item.memo, status=item.status,
                created_at=item.created_at,
            )
            for item in request.items
        ],
        created_at=request.created_at,
    )


@router.put("/items/{item_id}", response_model=ShoppingItemResponse)
async def update_shopping_item_endpoint(
    item_id: uuid.UUID,
    data: ShoppingItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await update_shopping_item(db, item_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="アイテムが見つかりません")

    return ShoppingItemResponse(
        id=str(item.id), item_name=item.item_name, category=item.category,
        quantity=item.quantity, memo=item.memo, status=item.status,
        is_excluded=item.is_excluded,
        created_at=item.created_at,
    )


@router.post("/requests/generate-from-menu", response_model=GenerateFromMenuResponse, status_code=status.HTTP_201_CREATED)
async def generate_from_menu_endpoint(
    data: GenerateFromMenuRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # week_start を月曜日に正規化
    week_start = data.week_start - timedelta(days=data.week_start.weekday())

    request, item_sources = await generate_shopping_list_from_menu(
        db,
        user_id=current_user.id,
        week_start=week_start,
        helper_user_id=current_user.id,
        notes=data.notes,
    )

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定週の献立が見つからないか、レシピが登録されていません",
        )

    # Reload with items
    request = await get_shopping_request_by_id(db, request.id)

    items_response = []
    excluded_count = 0
    for item in request.items:
        sources = item_sources.get(item.id, [])
        excluded_reason = "pantry" if item.is_excluded else None
        if item.is_excluded:
            excluded_count += 1
        items_response.append(GeneratedItemResponse(
            id=str(item.id),
            item_name=item.item_name,
            category=item.category,
            quantity=item.quantity,
            memo=item.memo,
            status=item.status,
            is_excluded=item.is_excluded,
            excluded_reason=excluded_reason,
            recipe_sources=sources,
        ))

    total = len(items_response)
    return GenerateFromMenuResponse(
        id=str(request.id),
        request_date=request.request_date,
        status=request.status,
        notes=request.notes,
        source_menu_week=week_start,
        items=items_response,
        summary=GenerateSummary(
            total_items=total,
            excluded_items=excluded_count,
            active_items=total - excluded_count,
        ),
        created_at=request.created_at,
    )


@router.post("/requests/{request_id}/organize", response_model=GenerateFromMenuResponse)
async def organize_shopping_request_endpoint(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """買い物リストをAIで整理（類似食材の統合・カテゴリ標準化）。"""
    try:
        request = await organize_shopping_request(db, current_user.id, request_id)
    except ShoppingRequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="買い物リクエストが見つかりません",
        )
    except OllamaUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="整理サービスに接続できません",
        )
    except OllamaTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="整理に時間がかかりすぎました。もう一度お試しください",
        )
    except (OllamaInvalidJSONError, OrganizeValidationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="整理結果の解析に失敗しました。もう一度お試しください",
        )

    items_response = []
    excluded_count = 0
    for item in request.items:
        excluded_reason = "pantry" if item.is_excluded else None
        if item.is_excluded:
            excluded_count += 1
        items_response.append(GeneratedItemResponse(
            id=str(item.id),
            item_name=item.item_name,
            category=item.category,
            quantity=item.quantity,
            memo=item.memo,
            status=item.status,
            is_excluded=item.is_excluded,
            excluded_reason=excluded_reason,
            recipe_sources=[],
        ))

    total = len(items_response)
    return GenerateFromMenuResponse(
        id=str(request.id),
        request_date=request.request_date,
        status=request.status,
        notes=request.notes,
        source_menu_week=request.request_date,
        items=items_response,
        summary=GenerateSummary(
            total_items=total,
            excluded_items=excluded_count,
            active_items=total - excluded_count,
        ),
        created_at=request.created_at,
    )


@router.put("/items/{item_id}/exclude", response_model=ExcludeResponse)
async def toggle_exclude_endpoint(
    item_id: uuid.UUID,
    data: ExcludeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShoppingItem).where(ShoppingItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="アイテムが見つかりません")

    item.is_excluded = data.is_excluded
    await db.flush()
    await db.refresh(item)

    return ExcludeResponse(
        id=str(item.id),
        item_name=item.item_name,
        is_excluded=item.is_excluded,
        status=item.status,
    )
