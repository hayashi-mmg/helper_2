"""ログ完全性検証のテスト。"""
import pytest

from app.services.log_integrity import LogIntegrityManager


HMAC_KEY = "test-hmac-key-for-integrity"


class TestLogIntegrityManager:
    """LogIntegrityManager の単体テスト。"""

    def setup_method(self):
        self.integrity = LogIntegrityManager(HMAC_KEY)

    def test_sign_entry_produces_hex_string(self):
        """署名はHEX文字列（64文字）を返す。"""
        log_data = {
            "accessor_user_id": "user-1",
            "accessor_email": "test@example.com",
            "access_type": "read",
        }
        signature = self.integrity.sign_entry(log_data)
        assert isinstance(signature, str)
        assert len(signature) == 64

    def test_sign_entry_deterministic(self):
        """同一データに対して同一署名を返す。"""
        log_data = {
            "accessor_user_id": "user-1",
            "accessor_email": "test@example.com",
            "access_type": "read",
        }
        sig1 = self.integrity.sign_entry(log_data)
        sig2 = self.integrity.sign_entry(log_data)
        assert sig1 == sig2

    def test_sign_entry_excludes_log_hash(self):
        """log_hashフィールドは署名対象から除外される。"""
        log_data = {
            "accessor_user_id": "user-1",
            "access_type": "read",
        }
        sig_without = self.integrity.sign_entry(log_data)

        log_data_with_hash = {**log_data, "log_hash": "some_previous_hash"}
        sig_with = self.integrity.sign_entry(log_data_with_hash)

        assert sig_without == sig_with

    def test_verify_entry_valid(self):
        """正しい署名を持つエントリは検証に通る。"""
        log_data = {
            "accessor_user_id": "user-1",
            "access_type": "read",
        }
        log_data["log_hash"] = self.integrity.sign_entry(log_data)
        assert self.integrity.verify_entry(log_data) is True

    def test_verify_entry_tampered(self):
        """改ざんされたエントリは検証に失敗する。"""
        log_data = {
            "accessor_user_id": "user-1",
            "access_type": "read",
        }
        log_data["log_hash"] = self.integrity.sign_entry(log_data)

        # 改ざん
        log_data["access_type"] = "export"
        assert self.integrity.verify_entry(log_data) is False

    def test_verify_entry_missing_hash(self):
        """log_hashが無いエントリは検証に失敗する。"""
        log_data = {
            "accessor_user_id": "user-1",
            "access_type": "read",
        }
        assert self.integrity.verify_entry(log_data) is False

    def test_different_keys_produce_different_signatures(self):
        """異なるHMAC鍵は異なる署名を生成する。"""
        other_integrity = LogIntegrityManager("different-key")
        log_data = {"accessor_user_id": "user-1", "access_type": "read"}

        sig1 = self.integrity.sign_entry(log_data)
        sig2 = other_integrity.sign_entry(log_data)
        assert sig1 != sig2
