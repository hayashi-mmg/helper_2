"""
ユーザーシードスクリプト
開発用デモユーザーをDBに登録する

Usage:
    cd backend
    python -m scripts.seed_users
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.database import async_session, engine
from app.db.models.user import User

USERS = [
    {
        "email": "senior@example.com",
        "password": "password123",
        "role": "senior",
        "full_name": "山田太郎",
        "phone": "090-1234-5678",
        "address": "東京都渋谷区神南1-2-3",
        "emergency_contact": "090-9876-5432",
        "medical_notes": "高血圧",
        "care_level": 2,
    },
    {
        "email": "helper@example.com",
        "password": "password123",
        "role": "helper",
        "full_name": "佐藤花子",
        "phone": "090-1111-2222",
        "certification_number": "H-12345",
    },
    {
        "email": "manager@example.com",
        "password": "password123",
        "role": "care_manager",
        "full_name": "鈴木次郎",
        "phone": "090-3333-4444",
    },
    {
        "email": "test@example.com",
        "password": "password123",
        "role": "helper",
        "full_name": "テストユーザー",
        "phone": "090-5555-6666",
        "certification_number": "H-99999",
    },
    {
        "email": "admin@example.com",
        "password": "password123",
        "role": "system_admin",
        "full_name": "管理者太郎",
        "phone": "090-7777-8888",
    },
]


async def seed_users():
    """デモユーザーをDBに登録する（既存はスキップ）"""
    async with async_session() as db:
        try:
            created = 0
            skipped = 0

            for user_data in USERS:
                email = user_data["email"]

                result = await db.execute(
                    select(User).where(User.email == email)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  スキップ（既存）: {email} ({existing.full_name})")
                    skipped += 1
                    continue

                data = {k: v for k, v in user_data.items() if k != "password"}
                data["password_hash"] = hash_password(user_data["password"])

                user = User(**data)
                db.add(user)
                await db.flush()

                print(f"  作成: {email} ({user_data['full_name']} / {user_data['role']})")
                created += 1

            await db.commit()
            print(f"\n完了: {created}件作成, {skipped}件スキップ（全{len(USERS)}件）")

        except Exception as e:
            await db.rollback()
            print(f"エラー: {e}")
            raise


async def main():
    print("=== ユーザーシードスクリプト開始 ===\n")
    await seed_users()
    print("\n=== 完了 ===")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
