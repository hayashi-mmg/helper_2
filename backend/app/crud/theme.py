"""Theme / UserPreference CRUD。"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.theme import Theme
from app.db.models.user_preference import UserPreference


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
async def get_theme_by_key(db: AsyncSession, theme_key: str) -> Theme | None:
    result = await db.execute(select(Theme).where(Theme.theme_key == theme_key))
    return result.scalar_one_or_none()


async def list_themes(
    db: AsyncSession,
    *,
    is_builtin: bool | None = None,
    is_active: bool | None = True,
) -> list[Theme]:
    query = select(Theme)
    if is_builtin is not None:
        query = query.where(Theme.is_builtin == is_builtin)
    if is_active is not None:
        query = query.where(Theme.is_active == is_active)
    query = query.order_by(Theme.is_builtin.desc(), Theme.theme_key)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_theme(
    db: AsyncSession,
    *,
    theme_key: str,
    name: str,
    description: str | None,
    definition: dict[str, Any],
    is_active: bool,
    created_by: uuid.UUID | None,
) -> Theme:
    theme = Theme(
        theme_key=theme_key,
        name=name,
        description=description,
        definition=definition,
        is_builtin=False,
        is_active=is_active,
        created_by=created_by,
    )
    db.add(theme)
    await db.flush()
    await db.refresh(theme)
    return theme


async def update_theme(
    db: AsyncSession,
    theme: Theme,
    *,
    name: str | None = None,
    description: str | None = None,
    definition: dict[str, Any] | None = None,
    is_active: bool | None = None,
) -> Theme:
    if name is not None:
        theme.name = name
    if description is not None:
        theme.description = description
    if definition is not None:
        theme.definition = definition
    if is_active is not None:
        theme.is_active = is_active
    await db.flush()
    await db.refresh(theme)
    return theme


async def delete_theme(db: AsyncSession, theme: Theme) -> None:
    await db.delete(theme)
    await db.flush()


# ---------------------------------------------------------------------------
# UserPreference
# ---------------------------------------------------------------------------
async def get_preference(db: AsyncSession, user_id: uuid.UUID, key: str) -> UserPreference | None:
    result = await db.execute(
        select(UserPreference).where(
            and_(UserPreference.user_id == user_id, UserPreference.preference_key == key)
        )
    )
    return result.scalar_one_or_none()


async def list_preferences(db: AsyncSession, user_id: uuid.UUID) -> list[UserPreference]:
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    return list(result.scalars().all())


async def upsert_preference(
    db: AsyncSession, user_id: uuid.UUID, key: str, value: Any
) -> UserPreference:
    """key-value を UPSERT。value は JSONB に格納される dict もしくは scalar。"""
    stored = value if isinstance(value, dict) else {"value": value}
    existing = await get_preference(db, user_id, key)
    if existing:
        existing.preference_value = stored
        await db.flush()
        await db.refresh(existing)
        return existing
    pref = UserPreference(user_id=user_id, preference_key=key, preference_value=stored)
    db.add(pref)
    await db.flush()
    await db.refresh(pref)
    return pref


def unwrap_preference_value(pref: UserPreference | None) -> Any:
    """格納時の `{"value": x}` ラッパーを外して元の値を返す。"""
    if pref is None:
        return None
    stored = pref.preference_value
    if isinstance(stored, dict) and set(stored.keys()) == {"value"}:
        return stored["value"]
    return stored
