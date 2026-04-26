"""管理者向け献立操作API（インポート等）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.core.database import get_db
from app.crud.admin_menu_import import import_menu_for_user
from app.db.models.user import User
from app.schemas.admin_menu_import import MenuImportRequest, MenuImportResponse

router = APIRouter(prefix="/admin/menus", tags=["管理：献立"])


@router.post("/import", response_model=MenuImportResponse)
async def admin_import_menu(
    data: MenuImportRequest,
    actor: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
) -> MenuImportResponse:
    """LLM等で生成した献立JSON（recipes + menu）を任意ユーザー宛に取り込み、

    必要なら買い物リストも同週で再生成する。`dry_run=true` でプレビュー。
    """
    return await import_menu_for_user(db, data, actor)
