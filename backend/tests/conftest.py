"""
テスト共通フィクスチャ。

テスト用 PostgreSQL データベースを使用。
各テスト後に TRUNCATE CASCADE で全データを削除。
"""
import uuid
from datetime import date, datetime, time, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.auth import create_access_token, hash_password
from app.core.config import settings
from app.core.database import Base, get_db
from app.db.models import (
    AuditLog,
    ComplianceLog,
    DataAccessLog,
    FrontendErrorLog,
    Message,
    Notification,
    PantryItem,
    QRToken,
    Recipe,
    RecipeIngredient,
    ShoppingItem,
    ShoppingRequest,
    SystemSetting,
    Task,
    TaskCompletion,
    User,
    UserAssignment,
    WeeklyMenu,
    WeeklyMenuRecipe,
)
from app.main import app

# ---------------------------------------------------------------------------
# テスト用 DB エンジン（アプリ側と完全に分離）
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/helper_db", "/helper_test_db")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# DB セットアップ / テアダウン
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """テストセッション開始時にテーブルを作成し、終了時に削除する。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """各テストの前にデータをクリーンアップ。"""
    cleanup_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with cleanup_engine.begin() as conn:
        await conn.exec_driver_sql(
            "TRUNCATE TABLE frontend_error_logs, compliance_logs, data_access_logs, "
            "notifications, system_settings, user_assignments, audit_logs, "
            "weekly_menu_recipes, weekly_menus, task_completions, tasks, "
            "shopping_items, shopping_requests, messages, qr_tokens, "
            "recipe_ingredients, pantry_items, recipes, users CASCADE"
        )
    await cleanup_engine.dispose()
    yield


# ---------------------------------------------------------------------------
# テストクライアント（アプリのDB依存をテスト用DBにオーバーライド）
# ---------------------------------------------------------------------------
def _create_test_app():
    """ミドルウェア問題を回避したテスト用アプリを作成。"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.v1.router import api_router
    from app.core.config import settings
    from app.monitoring.health import router as monitoring_router
    from app.sse.routes import router as sse_router
    from app.websocket.routes import router as ws_router

    from app.core.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware

    test_app = FastAPI(title="Test App")
    test_app.add_middleware(SecurityHeadersMiddleware)
    test_app.add_middleware(RequestLoggingMiddleware)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_app.include_router(api_router)
    test_app.include_router(ws_router)
    test_app.include_router(sse_router, prefix="/api/v1")
    test_app.include_router(monitoring_router, prefix="/api/v1")
    return test_app


_test_app = _create_test_app()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """FastAPI テストクライアント。BaseHTTPMiddleware を除外して安定実行。"""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    _test_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DBセッション（フィクスチャ用 - データ投入に使用）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """テストデータ投入用のDBセッション。"""
    async with TestSessionFactory() as session:
        yield session


# ---------------------------------------------------------------------------
# ユーザーフィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def senior_user(db: AsyncSession) -> User:
    user = User(
        email="senior@test.com",
        password_hash=hash_password("password123"),
        role="senior",
        full_name="テスト太郎",
        phone="090-1234-5678",
        address="東京都渋谷区",
        emergency_contact="090-9876-5432",
        medical_notes="高血圧",
        care_level=2,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def helper_user(db: AsyncSession) -> User:
    user = User(
        email="helper@test.com",
        password_hash=hash_password("password123"),
        role="helper",
        full_name="ヘルパー花子",
        phone="090-1111-2222",
        certification_number="H-12345",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def care_manager_user(db: AsyncSession) -> User:
    user = User(
        email="manager@test.com",
        password_hash=hash_password("password123"),
        role="care_manager",
        full_name="マネージャー次郎",
        phone="090-3333-4444",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db: AsyncSession) -> User:
    user = User(
        email="inactive@test.com",
        password_hash=hash_password("password123"),
        role="senior",
        full_name="無効ユーザー",
        is_active=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# トークンヘルパー
# ---------------------------------------------------------------------------
def make_token(user: User) -> str:
    return create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    })


def auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {make_token(user)}"}


# ---------------------------------------------------------------------------
# レシピフィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sample_recipe(db: AsyncSession, senior_user: User) -> Recipe:
    recipe = Recipe(
        user_id=senior_user.id,
        name="目玉焼き",
        category="和食",
        type="主菜",
        difficulty="簡単",
        cooking_time=5,
        ingredients="卵 2個\n油 少々",
        instructions="1. フライパンに油を引く\n2. 卵を割り入れる",
        is_active=True,
    )
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@pytest_asyncio.fixture
async def sample_recipes(db: AsyncSession, senior_user: User) -> list[Recipe]:
    recipes = []
    data = [
        ("味噌汁", "和食", "汁物", "簡単", 10),
        ("カレーライス", "洋食", "主菜", "普通", 45),
        ("チャーハン", "中華", "主菜", "普通", 20),
        ("サラダ", "洋食", "副菜", "簡単", 5),
        ("白ご飯", "和食", "ご飯", "簡単", 30),
    ]
    for name, cat, typ, diff, ct in data:
        r = Recipe(
            user_id=senior_user.id, name=name, category=cat, type=typ,
            difficulty=diff, cooking_time=ct, is_active=True,
        )
        db.add(r)
        recipes.append(r)
    await db.commit()
    for r in recipes:
        await db.refresh(r)
    return recipes


# ---------------------------------------------------------------------------
# タスクフィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sample_task(db: AsyncSession, senior_user: User, helper_user: User) -> Task:
    task = Task(
        senior_user_id=senior_user.id,
        helper_user_id=helper_user.id,
        title="朝食の準備",
        description="目玉焼きとトーストを作る",
        task_type="cooking",
        priority="high",
        estimated_minutes=30,
        scheduled_date=date.today(),
        scheduled_start_time=time(8, 0),
        scheduled_end_time=time(8, 30),
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# メッセージフィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sample_message(db: AsyncSession, senior_user: User, helper_user: User) -> Message:
    msg = Message(
        sender_id=helper_user.id,
        receiver_id=senior_user.id,
        content="おはようございます。今日もよろしくお願いします。",
        message_type="normal",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


# ---------------------------------------------------------------------------
# 買い物フィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sample_shopping_request(
    db: AsyncSession, senior_user: User, helper_user: User,
) -> ShoppingRequest:
    req = ShoppingRequest(
        senior_user_id=senior_user.id,
        helper_user_id=helper_user.id,
        request_date=date.today(),
        status="pending",
        notes="お願いします",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    items = [
        ShoppingItem(shopping_request_id=req.id, item_name="牛乳", category="食材", quantity="1本"),
        ShoppingItem(shopping_request_id=req.id, item_name="食パン", category="食材", quantity="1袋"),
        ShoppingItem(shopping_request_id=req.id, item_name="風邪薬", category="医薬品", quantity="1箱"),
    ]
    for item in items:
        db.add(item)
    await db.commit()
    return req


# ---------------------------------------------------------------------------
# レシピ食材フィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def recipe_with_ingredients(db: AsyncSession, senior_user: User) -> tuple[Recipe, list[RecipeIngredient]]:
    """食材付きのレシピを作成する。"""
    recipe = Recipe(
        user_id=senior_user.id,
        name="鶏肉の照り焼き",
        category="和食",
        type="主菜",
        difficulty="普通",
        cooking_time=30,
        ingredients="鶏もも肉 300g, しょうゆ 大さじ2, みりん 大さじ2",
        is_active=True,
    )
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)

    ingredients_data = [
        RecipeIngredient(recipe_id=recipe.id, name="鶏もも肉", quantity="300g", category="肉類", sort_order=1),
        RecipeIngredient(recipe_id=recipe.id, name="しょうゆ", quantity="大さじ2", category="調味料", sort_order=2),
        RecipeIngredient(recipe_id=recipe.id, name="みりん", quantity="大さじ2", category="調味料", sort_order=3),
        RecipeIngredient(recipe_id=recipe.id, name="砂糖", quantity="大さじ1", category="調味料", sort_order=4),
    ]
    for ing in ingredients_data:
        db.add(ing)
    await db.commit()
    for ing in ingredients_data:
        await db.refresh(ing)
    return recipe, ingredients_data


@pytest_asyncio.fixture
async def second_recipe_with_ingredients(db: AsyncSession, senior_user: User) -> tuple[Recipe, list[RecipeIngredient]]:
    """2つ目の食材付きレシピ（同名食材の集約テスト用）。"""
    recipe = Recipe(
        user_id=senior_user.id,
        name="親子丼",
        category="和食",
        type="主菜",
        difficulty="普通",
        cooking_time=25,
        is_active=True,
    )
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)

    ingredients_data = [
        RecipeIngredient(recipe_id=recipe.id, name="鶏もも肉", quantity="200g", category="肉類", sort_order=1),
        RecipeIngredient(recipe_id=recipe.id, name="卵", quantity="3個", category="卵・乳製品", sort_order=2),
        RecipeIngredient(recipe_id=recipe.id, name="しょうゆ", quantity="大さじ2", category="調味料", sort_order=3),
        RecipeIngredient(recipe_id=recipe.id, name="玉ねぎ", quantity="1個", category="野菜", sort_order=4),
    ]
    for ing in ingredients_data:
        db.add(ing)
    await db.commit()
    for ing in ingredients_data:
        await db.refresh(ing)
    return recipe, ingredients_data


# ---------------------------------------------------------------------------
# 献立+食材 統合フィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def menu_with_recipes(
    db: AsyncSession, senior_user: User,
    recipe_with_ingredients: tuple[Recipe, list[RecipeIngredient]],
    second_recipe_with_ingredients: tuple[Recipe, list[RecipeIngredient]],
) -> WeeklyMenu:
    """食材付きレシピ2つを含む週間献立を作成する。"""
    recipe1, _ = recipe_with_ingredients
    recipe2, _ = second_recipe_with_ingredients

    week_start = date.today() - timedelta(days=date.today().weekday())  # This Monday

    menu = WeeklyMenu(user_id=senior_user.id, week_start=week_start)
    db.add(menu)
    await db.commit()
    await db.refresh(menu)

    entries = [
        WeeklyMenuRecipe(weekly_menu_id=menu.id, recipe_id=recipe1.id, day_of_week=1, meal_type="dinner", recipe_type="主菜"),
        WeeklyMenuRecipe(weekly_menu_id=menu.id, recipe_id=recipe2.id, day_of_week=2, meal_type="dinner", recipe_type="主菜"),
    ]
    for entry in entries:
        db.add(entry)
    await db.commit()
    return menu


# ---------------------------------------------------------------------------
# パントリーフィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def sample_pantry(db: AsyncSession, senior_user: User) -> list[PantryItem]:
    """パントリーアイテムを作成する。"""
    items = [
        PantryItem(user_id=senior_user.id, name="しょうゆ", category="調味料", is_available=True),
        PantryItem(user_id=senior_user.id, name="みりん", category="調味料", is_available=True),
        PantryItem(user_id=senior_user.id, name="米", category="穀類", is_available=False),
    ]
    for item in items:
        db.add(item)
    await db.commit()
    for item in items:
        await db.refresh(item)
    return items


# ---------------------------------------------------------------------------
# 管理者フィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin@test.com",
        password_hash=hash_password("password123"),
        role="system_admin",
        full_name="管理者太郎",
        phone="090-5555-6666",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_assignment(
    db: AsyncSession, senior_user: User, helper_user: User, admin_user: User,
) -> UserAssignment:
    assignment = UserAssignment(
        helper_id=helper_user.id,
        senior_id=senior_user.id,
        assigned_by=admin_user.id,
        status="active",
        visit_frequency="週3回",
        preferred_days=[1, 3, 5],
        start_date=date.today(),
        notes="午前中の訪問��希望",
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@pytest_asyncio.fixture
async def sample_setting(db: AsyncSession) -> SystemSetting:
    setting = SystemSetting(
        setting_key="password_min_length",
        setting_value={"value": 8},
        category="security",
        description="パスワード最小文字数",
    )
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return setting


@pytest_asyncio.fixture
async def sample_notification(db: AsyncSession, senior_user: User) -> Notification:
    notif = Notification(
        user_id=senior_user.id,
        title="テスト通知",
        body="テスト通知の本文です",
        notification_type="system",
        priority="normal",
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif
