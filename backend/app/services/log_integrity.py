"""ログ完全性検証サービス。

HMAC-SHA256署名 + 日次チェーンハッシュでログの改ざん・削除を検知する。
"""
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.compliance_log import ComplianceLog
from app.db.models.data_access_log import DataAccessLog
from app.db.models.system_setting import SystemSetting


class LogIntegrityManager:
    def __init__(self, hmac_key: str):
        self.hmac_key = hmac_key.encode()

    def sign_entry(self, log_data: dict) -> str:
        """ログエントリのHMAC-SHA256署名を生成する。"""
        signable = {k: v for k, v in log_data.items() if k != "log_hash"}
        message = json.dumps(signable, sort_keys=True, default=str)
        return hmac.new(self.hmac_key, message.encode(), hashlib.sha256).hexdigest()

    def verify_entry(self, log_data: dict) -> bool:
        """ログエントリの署名を検証する。"""
        expected_hash = log_data.get("log_hash")
        if not expected_hash:
            return False
        computed_hash = self.sign_entry(log_data)
        return hmac.compare_digest(expected_hash, computed_hash)


async def compute_daily_chain_hash(
    db: AsyncSession,
    target_date: date,
    hmac_key: str,
) -> dict:
    """指定日の全エントリからチェーンハッシュを計算する。"""
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    # 前日のチェーンハッシュを取得
    previous_key = f"log_chain_hash_{(target_date - timedelta(days=1)).isoformat()}"
    prev_result = await db.execute(
        select(SystemSetting).where(SystemSetting.setting_key == previous_key)
    )
    prev_setting = prev_result.scalar_one_or_none()
    previous_hash = prev_setting.setting_value.get("hash", "") if prev_setting else ""

    # 当日のdata_access_logsのlog_hashを収集
    dal_result = await db.execute(
        select(DataAccessLog.log_hash)
        .where(and_(DataAccessLog.created_at >= day_start, DataAccessLog.created_at < day_end))
        .order_by(DataAccessLog.created_at)
    )
    dal_hashes = [row[0] or "" for row in dal_result.all()]

    # 当日のcompliance_logsのlog_hashを収集
    cl_result = await db.execute(
        select(ComplianceLog.log_hash)
        .where(and_(ComplianceLog.created_at >= day_start, ComplianceLog.created_at < day_end))
        .order_by(ComplianceLog.created_at)
    )
    cl_hashes = [row[0] or "" for row in cl_result.all()]

    all_hashes = dal_hashes + cl_hashes
    combined = previous_hash + "".join(all_hashes)
    chain_hash = hashlib.sha256(combined.encode()).hexdigest()

    return {
        "hash": chain_hash,
        "entry_count": len(all_hashes),
        "tables": ["data_access_logs", "compliance_logs"],
        "computed_at": datetime.utcnow().isoformat(),
    }


async def verify_daily_chain_hash(
    db: AsyncSession,
    target_date: date,
    hmac_key: str,
) -> tuple[bool, str]:
    """指定日のチェーンハッシュを再計算し、保存済みハッシュと比較する。"""
    setting_key = f"log_chain_hash_{target_date.isoformat()}"
    stored_result = await db.execute(
        select(SystemSetting).where(SystemSetting.setting_key == setting_key)
    )
    stored_setting = stored_result.scalar_one_or_none()

    if not stored_setting:
        return False, "チェーンハッシュが未計算です"

    stored_hash = stored_setting.setting_value.get("hash", "")
    computed = await compute_daily_chain_hash(db, target_date, hmac_key)

    if computed["hash"] != stored_hash:
        return False, f"チェーンハッシュ不一致: stored={stored_hash[:16]}... computed={computed['hash'][:16]}..."

    return True, "検証成功"


async def verify_entries_for_date(
    db: AsyncSession,
    target_date: date,
    hmac_key: str,
) -> list[dict]:
    """指定日の全エントリの個別署名を検証し、不正なエントリを返す。"""
    integrity = LogIntegrityManager(hmac_key)
    invalid_entries = []

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    # data_access_logs
    dal_result = await db.execute(
        select(DataAccessLog)
        .where(and_(DataAccessLog.created_at >= day_start, DataAccessLog.created_at < day_end))
    )
    for log in dal_result.scalars().all():
        log_dict = {
            "accessor_user_id": log.accessor_user_id,
            "accessor_email": log.accessor_email,
            "accessor_role": log.accessor_role,
            "target_user_id": log.target_user_id,
            "target_user_name": log.target_user_name,
            "access_type": log.access_type,
            "resource_type": log.resource_type,
            "data_fields": log.data_fields,
            "endpoint": log.endpoint,
            "http_method": log.http_method,
            "ip_address": str(log.ip_address),
            "user_agent": log.user_agent,
            "has_assignment": log.has_assignment,
            "log_hash": log.log_hash,
        }
        if not integrity.verify_entry(log_dict):
            invalid_entries.append({
                "table": "data_access_logs",
                "id": str(log.id),
                "created_at": log.created_at.isoformat(),
            })

    return invalid_entries
