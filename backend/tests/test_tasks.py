"""作業管理 API テスト。

仕様: GET /tasks/today, POST /tasks, PUT /tasks/{id}, DELETE /tasks/{id},
      PUT /tasks/{id}/complete, POST /tasks/reports/daily
"""
import uuid
from datetime import date, time

import pytest
from httpx import AsyncClient

from app.db.models import Task, User
from tests.conftest import auth_headers


class TestGetTodayTasks:
    """本日のタスク取得テスト。"""

    async def test_get_today_tasks(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """ヘルパーが本日のタスクを取得できること。"""
        res = await client.get("/api/v1/tasks/today", headers=auth_headers(helper_user))
        assert res.status_code == 200
        tasks = res.json()
        assert len(tasks) >= 1
        assert tasks[0]["title"] == "朝食の準備"
        assert tasks[0]["task_type"] == "cooking"
        assert tasks[0]["priority"] == "high"

    async def test_get_tasks_with_date(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """指定日のタスクを取得できること。"""
        res = await client.get(
            "/api/v1/tasks/today",
            params={"date": str(date.today())},
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 200
        assert len(res.json()) >= 1

    async def test_get_tasks_empty_date(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """タスクのない日付で空リストが返ること。"""
        res = await client.get(
            "/api/v1/tasks/today",
            params={"date": "2099-01-01"},
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 200
        assert res.json() == []

    async def test_get_tasks_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.get("/api/v1/tasks/today")
        assert res.status_code == 401


class TestCreateTask:
    """タスク作成テスト。"""

    async def test_create_success(self, client: AsyncClient, helper_user: User, senior_user: User):
        """タスクを作成できること。"""
        res = await client.post(
            "/api/v1/tasks",
            headers=auth_headers(helper_user),
            json={
                "senior_user_id": str(senior_user.id),
                "title": "掃除",
                "task_type": "cleaning",
                "priority": "medium",
                "scheduled_date": str(date.today()),
                "estimated_minutes": 60,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "掃除"
        assert data["task_type"] == "cleaning"
        assert data["status"] == "pending"
        assert data["helper_user_id"] == str(helper_user.id)

    async def test_create_all_task_types(self, client: AsyncClient, helper_user: User, senior_user: User):
        """全タスクタイプ（cooking, cleaning, shopping, special）が作成できること。"""
        for task_type in ["cooking", "cleaning", "shopping", "special"]:
            res = await client.post(
                "/api/v1/tasks",
                headers=auth_headers(helper_user),
                json={
                    "senior_user_id": str(senior_user.id),
                    "title": f"{task_type}タスク",
                    "task_type": task_type,
                    "scheduled_date": str(date.today()),
                },
            )
            assert res.status_code == 201, f"Failed for type: {task_type}"

    async def test_create_invalid_task_type(self, client: AsyncClient, helper_user: User, senior_user: User):
        """無効なタスクタイプで 422 が返ること。"""
        res = await client.post(
            "/api/v1/tasks",
            headers=auth_headers(helper_user),
            json={
                "senior_user_id": str(senior_user.id),
                "title": "不正タスク",
                "task_type": "invalid",
                "scheduled_date": str(date.today()),
            },
        )
        assert res.status_code == 422

    async def test_create_invalid_priority(self, client: AsyncClient, helper_user: User, senior_user: User):
        """無効な優先度で 422 が返ること。"""
        res = await client.post(
            "/api/v1/tasks",
            headers=auth_headers(helper_user),
            json={
                "senior_user_id": str(senior_user.id),
                "title": "不正タスク",
                "task_type": "cooking",
                "priority": "urgent",
                "scheduled_date": str(date.today()),
            },
        )
        assert res.status_code == 422


class TestUpdateTask:
    """タスク更新テスト。"""

    async def test_update_status(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """タスクステータスを更新できること。"""
        res = await client.put(
            f"/api/v1/tasks/{sample_task.id}",
            headers=auth_headers(helper_user),
            json={"status": "in_progress"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"

    async def test_update_title(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """タスクタイトルを更新できること。"""
        res = await client.put(
            f"/api/v1/tasks/{sample_task.id}",
            headers=auth_headers(helper_user),
            json={"title": "昼食の準備に変更"},
        )
        assert res.status_code == 200
        assert res.json()["title"] == "昼食の準備に変更"

    async def test_update_not_found(self, client: AsyncClient, helper_user: User):
        """存在しないタスクの更新で 404 が返ること。"""
        res = await client.put(
            f"/api/v1/tasks/{uuid.uuid4()}",
            headers=auth_headers(helper_user),
            json={"title": "存在しない"},
        )
        assert res.status_code == 404


class TestDeleteTask:
    """タスク削除テスト（論理削除: status = cancelled）。"""

    async def test_delete_success(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """タスクを削除（キャンセル）できること。"""
        res = await client.delete(
            f"/api/v1/tasks/{sample_task.id}",
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 204

    async def test_delete_not_found(self, client: AsyncClient, helper_user: User):
        """存在しないタスクの削除で 404 が返ること。"""
        res = await client.delete(
            f"/api/v1/tasks/{uuid.uuid4()}",
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 404


class TestCompleteTask:
    """タスク完了テスト。"""

    async def test_complete_success(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """タスクを完了できること。"""
        res = await client.put(
            f"/api/v1/tasks/{sample_task.id}/complete",
            headers=auth_headers(helper_user),
            json={
                "actual_minutes": 25,
                "notes": "問題なく完了",
                "next_notes": "次回は卵を3個に",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "completed_at" in data
        assert data["message"] == "作業を完了しました"

    async def test_complete_minimal(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """最小限の情報でタスクを完了できること。"""
        res = await client.put(
            f"/api/v1/tasks/{sample_task.id}/complete",
            headers=auth_headers(helper_user),
            json={},
        )
        assert res.status_code == 200

    async def test_complete_not_found(self, client: AsyncClient, helper_user: User):
        """存在しないタスクの完了で 404 が返ること。"""
        res = await client.put(
            f"/api/v1/tasks/{uuid.uuid4()}/complete",
            headers=auth_headers(helper_user),
            json={"notes": "不正"},
        )
        assert res.status_code == 404


class TestDailyReport:
    """日次レポートテスト。"""

    async def test_report_success(self, client: AsyncClient, helper_user: User, sample_task: Task):
        """日次レポートが生成されること。"""
        res = await client.post(
            "/api/v1/tasks/reports/daily",
            headers=auth_headers(helper_user),
            json={"date": str(date.today())},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["date"] == str(date.today())
        assert "summary" in data
        assert "tasks" in data
        assert data["summary"]["total_tasks"] >= 1

    async def test_report_empty_date(self, client: AsyncClient, helper_user: User):
        """タスクのない日のレポートも生成されること。"""
        res = await client.post(
            "/api/v1/tasks/reports/daily",
            headers=auth_headers(helper_user),
            json={"date": "2099-01-01"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_tasks"] == 0
        assert data["tasks"] == []
