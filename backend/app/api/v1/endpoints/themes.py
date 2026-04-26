"""テーマシステム API。

docs/api_specification.md §16
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.crud import theme as crud_theme
from app.crud.admin import create_audit_log, get_setting, update_setting
from app.crud.theme import unwrap_preference_value
from app.db.models.theme import Theme
from app.db.models.user import User
from app.schemas.theme import (
    ThemeCreate,
    ThemeRead,
    ThemeSummary,
    ThemeSummaryListResponse,
    ThemeUpdate,
)
from app.schemas.user_preference import UserPreferencesRead, UserPreferencesUpdate
from app.services.theme_validator import ThemeValidationError, validate_theme_definition


router = APIRouter(tags=["テーマ"])


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------
def _theme_to_read(theme: Theme) -> ThemeRead:
    return ThemeRead(
        theme_key=theme.theme_key,
        name=theme.name,
        description=theme.description,
        definition=theme.definition,
        is_builtin=theme.is_builtin,
        is_active=theme.is_active,
        updated_at=theme.updated_at,
    )


def _theme_to_summary(theme: Theme) -> ThemeSummary:
    preview = None
    meta = theme.definition.get("meta") if isinstance(theme.definition, dict) else None
    if isinstance(meta, dict):
        preview = meta.get("previewImageUrl")
    return ThemeSummary(
        theme_key=theme.theme_key,
        name=theme.name,
        description=theme.description,
        is_builtin=theme.is_builtin,
        is_active=theme.is_active,
        preview_image_url=preview,
        updated_at=theme.updated_at,
    )


def _raise_validation_error(exc: ThemeValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "THEME_VALIDATION_FAILED", "errors": exc.errors},
    )


async def _resolve_default_theme(db: AsyncSession) -> Theme:
    """現在のシステム既定テーマを返す。解決不能な場合は standard プリセットへフォールバック。"""
    setting = await get_setting(db, "default_theme_id")
    default_key = None
    if setting is not None:
        val = setting.setting_value
        if isinstance(val, dict) and "value" in val:
            default_key = val["value"]
        elif isinstance(val, str):
            default_key = val

    for key in [default_key, "standard"]:
        if not key:
            continue
        theme = await crud_theme.get_theme_by_key(db, key)
        if theme and theme.is_active:
            return theme
    raise HTTPException(status_code=500, detail="既定テーマが利用できません")


# ---------------------------------------------------------------------------
# 公開エンドポイント
# ---------------------------------------------------------------------------
@router.get("/themes/public/default", response_model=ThemeRead)
async def get_public_default_theme(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    theme = await _resolve_default_theme(db)
    response.headers["Cache-Control"] = "public, max-age=300"
    return _theme_to_read(theme)


# ---------------------------------------------------------------------------
# 認証ユーザー向け
# ---------------------------------------------------------------------------
@router.get("/themes", response_model=ThemeSummaryListResponse)
async def list_themes_endpoint(
    is_builtin: bool | None = None,
    is_active: bool | None = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    themes = await crud_theme.list_themes(db, is_builtin=is_builtin, is_active=is_active)
    return ThemeSummaryListResponse(themes=[_theme_to_summary(t) for t in themes])


@router.get("/themes/{theme_key}", response_model=ThemeRead)
async def get_theme_endpoint(
    theme_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    theme = await crud_theme.get_theme_by_key(db, theme_key)
    if not theme or not theme.is_active:
        raise HTTPException(
            status_code=404,
            detail={"code": "THEME_NOT_FOUND", "message": "テーマが見つかりません"},
        )
    return _theme_to_read(theme)


# ---------------------------------------------------------------------------
# ユーザー設定
# ---------------------------------------------------------------------------
@router.get("/users/me/preferences", response_model=UserPreferencesRead)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await crud_theme.list_preferences(db, current_user.id)
    by_key = {p.preference_key: unwrap_preference_value(p) for p in prefs}
    return UserPreferencesRead(
        theme_id=by_key.get("theme_id"),
        font_size_override=by_key.get("font_size_override"),
    )


@router.put("/users/me/preferences", response_model=UserPreferencesRead)
async def update_my_preferences(
    data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.theme_id is not None:
        theme = await crud_theme.get_theme_by_key(db, data.theme_id)
        if not theme or not theme.is_active:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "THEME_INACTIVE" if theme else "THEME_NOT_FOUND",
                    "message": "指定されたテーマは選択できません",
                },
            )
        await crud_theme.upsert_preference(db, current_user.id, "theme_id", data.theme_id)

    if data.font_size_override is not None:
        await crud_theme.upsert_preference(
            db, current_user.id, "font_size_override", data.font_size_override
        )

    prefs = await crud_theme.list_preferences(db, current_user.id)
    by_key = {p.preference_key: unwrap_preference_value(p) for p in prefs}
    return UserPreferencesRead(
        theme_id=by_key.get("theme_id"),
        font_size_override=by_key.get("font_size_override"),
    )


# ---------------------------------------------------------------------------
# 管理者向け
# ---------------------------------------------------------------------------
@router.post(
    "/admin/themes",
    response_model=ThemeRead,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_theme(
    data: ThemeCreate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    if await crud_theme.get_theme_by_key(db, data.theme_key):
        raise HTTPException(
            status_code=409,
            detail={"code": "THEME_KEY_CONFLICT", "message": "同名のテーマが既に存在します"},
        )

    # definition 内の id を theme_key と揃える
    definition = dict(data.definition)
    definition["id"] = data.theme_key

    try:
        validate_theme_definition(definition)
    except ThemeValidationError as exc:
        _raise_validation_error(exc)

    theme = await crud_theme.create_theme(
        db,
        theme_key=data.theme_key,
        name=data.name,
        description=data.description,
        definition=definition,
        is_active=data.is_active,
        created_by=current_user.id,
    )
    await create_audit_log(
        db,
        user=current_user,
        action="theme.create",
        resource_type="theme",
        resource_id=theme.id,
        changes={"theme_key": theme.theme_key, "name": theme.name},
    )
    return _theme_to_read(theme)


@router.put("/admin/themes/{theme_key}", response_model=ThemeRead)
async def admin_update_theme(
    theme_key: str,
    data: ThemeUpdate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    theme = await crud_theme.get_theme_by_key(db, theme_key)
    if not theme:
        raise HTTPException(
            status_code=404,
            detail={"code": "THEME_NOT_FOUND", "message": "テーマが見つかりません"},
        )

    # 組込みテーマは definition 変更不可
    if theme.is_builtin and data.definition is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "THEME_BUILTIN_IMMUTABLE",
                "message": "組込みテーマの definition は変更できません",
            },
        )

    if data.definition is not None:
        definition = dict(data.definition)
        definition["id"] = theme_key
        try:
            validate_theme_definition(definition)
        except ThemeValidationError as exc:
            _raise_validation_error(exc)
        data_definition = definition
    else:
        data_definition = None

    old_values = {"name": theme.name, "description": theme.description, "is_active": theme.is_active}
    theme = await crud_theme.update_theme(
        db,
        theme,
        name=data.name,
        description=data.description,
        definition=data_definition,
        is_active=data.is_active,
    )
    await create_audit_log(
        db,
        user=current_user,
        action="theme.update",
        resource_type="theme",
        resource_id=theme.id,
        changes={
            "theme_key": theme_key,
            "old": old_values,
            "new": {"name": theme.name, "description": theme.description, "is_active": theme.is_active},
        },
    )
    return _theme_to_read(theme)


@router.delete(
    "/admin/themes/{theme_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_theme(
    theme_key: str,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    theme = await crud_theme.get_theme_by_key(db, theme_key)
    if not theme:
        raise HTTPException(
            status_code=404,
            detail={"code": "THEME_NOT_FOUND", "message": "テーマが見つかりません"},
        )

    if theme.is_builtin:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "THEME_BUILTIN_DELETE_FORBIDDEN",
                "message": "組込みテーマは削除できません",
            },
        )

    # 既定テーマに指定中であれば削除不可
    default_setting = await get_setting(db, "default_theme_id")
    if default_setting is not None:
        default_val = default_setting.setting_value
        default_key = default_val["value"] if isinstance(default_val, dict) else default_val
        if default_key == theme_key:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "THEME_IN_USE_AS_DEFAULT",
                    "message": "既定テーマに指定されているテーマは削除できません",
                },
            )

    await create_audit_log(
        db,
        user=current_user,
        action="theme.delete",
        resource_type="theme",
        resource_id=theme.id,
        changes={"theme_key": theme_key, "snapshot": {"name": theme.name}},
    )
    await crud_theme.delete_theme(db, theme)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# 既定テーマの変更(admin_system.update_setting より優先するため themes ルータに配置)
# ---------------------------------------------------------------------------
@router.put("/admin/settings/default_theme_id")
async def admin_set_default_theme(
    data: dict,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    value = data.get("value") if isinstance(data, dict) else None
    if not isinstance(value, str):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_VALUE", "message": "value は theme_key 文字列である必要があります"},
        )

    theme = await crud_theme.get_theme_by_key(db, value)
    if not theme:
        raise HTTPException(
            status_code=422,
            detail={"code": "THEME_NOT_FOUND", "message": "テーマが見つかりません"},
        )
    if not theme.is_active:
        raise HTTPException(
            status_code=422,
            detail={"code": "THEME_INACTIVE", "message": "無効化されたテーマは既定にできません"},
        )

    setting = await get_setting(db, "default_theme_id")
    if not setting:
        raise HTTPException(
            status_code=404,
            detail={"code": "SETTING_NOT_FOUND", "message": "default_theme_id が初期化されていません"},
        )

    old_value = setting.setting_value
    setting = await update_setting(db, setting, value, current_user.id)
    await create_audit_log(
        db,
        user=current_user,
        action="system.update_default_theme",
        resource_type="system_setting",
        changes={"setting_key": "default_theme_id", "old": str(old_value), "new": value},
    )

    return {
        "setting_key": "default_theme_id",
        "value": value,
        "updated_at": setting.updated_at,
    }
