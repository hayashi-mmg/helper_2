# セキュリティ実装仕様書

## 文書管理情報
- **文書番号**: SEC-IMPL-001
- **版数**: 1.0
- **作成日**: 2025年7月13日
- **最終更新日**: 2025年7月13日
- **設計者**: Claude Code + Gemini セキュリティ検証

---

## 1. セキュリティ概要

### 1.1 セキュリティポリシー
高齢者の個人情報・健康情報を扱うため、**防御多層化（Defense in Depth）**を基本戦略とし、以下の原則に従う：

- **最小権限の原則**：必要最小限のアクセス権限のみ付与
- **データ最小化**：必要最小限のデータのみ収集・保存
- **暗号化原則**：保存時・転送時の暗号化
- **監査証跡**：全アクセス・操作の記録
- **定期的検証**：セキュリティ状況の継続監視

### 1.2 準拠法令・ガイドライン
- **個人情報保護法**（改正版）
- **医療・介護分野におけるサイバーセキュリティ対策ガイドライン**
- **OWASP Top 10**（Webアプリケーションセキュリティ）
- **NIST Cybersecurity Framework**

### 1.3 脅威モデル

#### 1.3.1 想定脅威
| 脅威カテゴリ | 具体的脅威 | 影響度 | 発生確率 |
|-------------|-----------|-------|----------|
| **不正アクセス** | SQLインジェクション、認証回避 | 高 | 中 |
| **データ漏洩** | 個人情報・健康情報の漏洩 | 極高 | 中 |
| **サービス妨害** | DDoS攻撃、システムダウン | 中 | 高 |
| **内部脅威** | 権限乱用、情報持ち出し | 高 | 低 |
| **フィッシング** | 偽サイトによる認証情報窃取 | 高 | 中 |

#### 1.3.2 資産分類
| 資産 | 機密性 | 完全性 | 可用性 |
|------|-------|-------|-------|
| **利用者個人情報** | 極高 | 高 | 中 |
| **健康・医療情報** | 極高 | 極高 | 高 |
| **認証情報** | 極高 | 極高 | 高 |
| **システム設定** | 高 | 極高 | 極高 |
| **通信ログ** | 中 | 高 | 中 |

---

## 2. 認証・認可システム

### 2.1 JWT実装詳細

#### 2.1.1 トークン戦略
```python
# backend/app/core/auth.py
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

class JWTManager:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = 30  # 短期間
        self.refresh_token_expire_days = 7     # 長期間
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """アクセストークン生成"""
        to_encode = user_data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": self._generate_jti()  # JWT ID（トークン無効化用）
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """リフレッシュトークン生成"""
        to_encode = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": self._generate_jti()
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """トークン検証"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # トークンタイプ確認
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # JTI（JWT ID）がブラックリストに含まれていないか確認
            if await self._is_token_blacklisted(payload.get("jti")):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    async def revoke_token(self, jti: str):
        """トークン無効化（ブラックリスト登録）"""
        await redis_client.setex(f"blacklist:{jti}", 
                                timedelta(days=self.refresh_token_expire_days).total_seconds(), 
                                "revoked")
    
    def _generate_jti(self) -> str:
        """JWT ID生成"""
        import uuid
        return str(uuid.uuid4())
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """ブラックリスト確認"""
        return await redis_client.exists(f"blacklist:{jti}")
```

#### 2.1.2 パスワードハッシュ化
```python
# backend/app/core/security.py
import bcrypt
import secrets
from typing import Union

class PasswordManager:
    def __init__(self):
        self.bcrypt_rounds = 12  # 計算コスト（セキュリティ vs パフォーマンス）
    
    def hash_password(self, password: str) -> str:
        """パスワードハッシュ化"""
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """パスワード検証"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def generate_secure_password(self, length: int = 12) -> str:
        """安全なパスワード生成（初期パスワード用）"""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """パスワード強度検証"""
        errors = []
        
        if len(password) < 8:
            errors.append("パスワードは8文字以上である必要があります")
        
        if not any(c.islower() for c in password):
            errors.append("小文字を含む必要があります")
        
        if not any(c.isupper() for c in password):
            errors.append("大文字を含む必要があります")
        
        if not any(c.isdigit() for c in password):
            errors.append("数字を含む必要があります")
        
        # 一般的なパスワードチェック
        common_passwords = ["password", "123456", "password123"]
        if password.lower() in common_passwords:
            errors.append("よく使われるパスワードです。別のパスワードを選択してください")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "strength": self._calculate_strength(password)
        }
    
    def _calculate_strength(self, password: str) -> str:
        """パスワード強度計算"""
        score = 0
        
        if len(password) >= 8: score += 1
        if len(password) >= 12: score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isupper() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password): score += 1
        
        if score >= 5: return "強い"
        elif score >= 3: return "普通"
        else: return "弱い"
```

### 2.2 QRコード認証システム

#### 2.2.1 QRトークン生成
```python
# backend/app/core/qr_auth.py
import qrcode
import secrets
from datetime import datetime, timedelta
from typing import Optional
from io import BytesIO
import base64

class QRAuthManager:
    def __init__(self):
        self.token_expire_hours = 24  # 24時間有効
        self.max_uses = 1            # ワンタイム使用
    
    async def generate_qr_token(self, user_id: str, purpose: str = "login") -> Dict[str, Any]:
        """QRコード用トークン生成"""
        # ランダムトークン生成
        token = secrets.token_urlsafe(32)
        
        # トークンデータ
        token_data = {
            "user_id": user_id,
            "purpose": purpose,
            "expires_at": datetime.utcnow() + timedelta(hours=self.token_expire_hours),
            "max_uses": self.max_uses,
            "use_count": 0,
            "created_at": datetime.utcnow()
        }
        
        # データベースに保存
        qr_token = QRToken(
            token_hash=self._hash_token(token),
            user_id=user_id,
            purpose=purpose,
            expires_at=token_data["expires_at"],
            max_uses=self.max_uses
        )
        
        await self._save_qr_token(qr_token)
        
        # QRコード画像生成
        qr_url = f"{settings.FRONTEND_URL}/qr/{token}"
        qr_image_base64 = self._generate_qr_image(qr_url)
        
        return {
            "qr_url": qr_url,
            "qr_code_base64": qr_image_base64,
            "expires_at": token_data["expires_at"].isoformat(),
            "purpose": purpose
        }
    
    async def validate_qr_token(self, token: str) -> Dict[str, Any]:
        """QRトークン検証"""
        token_hash = self._hash_token(token)
        qr_token = await self._get_qr_token(token_hash)
        
        if not qr_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid QR token"
            )
        
        # 有効期限チェック
        if datetime.utcnow() > qr_token.expires_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="QR token has expired"
            )
        
        # 使用回数チェック
        if qr_token.use_count >= qr_token.max_uses:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="QR token has been used"
            )
        
        # 使用回数を増加
        await self._increment_token_usage(qr_token.id)
        
        # 通常のアクセストークン生成
        user = await self._get_user(qr_token.user_id)
        access_token = jwt_manager.create_access_token({
            "sub": user.id,
            "email": user.email,
            "role": user.role
        })
        
        return {
            "valid": True,
            "user_id": qr_token.user_id,
            "purpose": qr_token.purpose,
            "access_token": access_token,
            "redirect_url": self._get_redirect_url(user.role)
        }
    
    def _generate_qr_image(self, data: str) -> str:
        """QRコード画像生成"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # 画像生成
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Base64エンコード
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def _hash_token(self, token: str) -> str:
        """トークンハッシュ化"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
```

### 2.3 セッション管理

#### 2.3.1 Redis セッションストア
```python
# backend/app/core/session.py
import json
import redis.asyncio as redis
from datetime import timedelta

class SessionManager:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.session_expire_minutes = 480  # 8時間
    
    async def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """セッション作成"""
        session_id = secrets.token_urlsafe(32)
        
        session_info = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            **session_data
        }
        
        await self.redis_client.setex(
            f"session:{session_id}",
            timedelta(minutes=self.session_expire_minutes).total_seconds(),
            json.dumps(session_info)
        )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション取得"""
        session_data = await self.redis_client.get(f"session:{session_id}")
        
        if not session_data:
            return None
        
        session_info = json.loads(session_data)
        
        # アクセス時刻更新
        session_info["last_accessed"] = datetime.utcnow().isoformat()
        await self.redis_client.setex(
            f"session:{session_id}",
            timedelta(minutes=self.session_expire_minutes).total_seconds(),
            json.dumps(session_info)
        )
        
        return session_info
    
    async def delete_session(self, session_id: str):
        """セッション削除"""
        await self.redis_client.delete(f"session:{session_id}")
    
    async def cleanup_expired_sessions(self):
        """期限切れセッション削除"""
        # Redisの自動削除機能を使用するため、特別な処理は不要
        pass
```

---

## 3. 入力検証・サニタイゼーション

### 3.1 Pydantic バリデーション

#### 3.1.1 基本バリデーター
```python
# backend/app/schemas/validators.py
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
import re

class UserRegistrationSchema(BaseModel):
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., min_length=8, max_length=100, description="パスワード")
    full_name: str = Field(..., min_length=1, max_length=100, description="氏名")
    phone: Optional[str] = Field(None, max_length=20, description="電話番号")
    role: str = Field(..., regex="^(senior|helper|care_manager)$", description="ユーザー種別")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            # 日本の電話番号形式チェック
            phone_pattern = r'^(\+81|0)[0-9]{1,4}-?[0-9]{1,4}-?[0-9]{3,4}$'
            if not re.match(phone_pattern, v):
                raise ValueError('有効な電話番号を入力してください')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        # HTMLタグ除去
        import bleach
        cleaned = bleach.clean(v, tags=[], strip=True)
        if len(cleaned.strip()) == 0:
            raise ValueError('氏名を入力してください')
        return cleaned.strip()

class RecipeSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="料理名")
    category: str = Field(..., regex="^(和食|洋食|中華|その他)$", description="カテゴリ")
    type: str = Field(..., regex="^(主菜|副菜|汁物|ご飯|その他)$", description="料理タイプ")
    difficulty: str = Field(..., regex="^(簡単|普通|難しい)$", description="難易度")
    cooking_time: int = Field(..., ge=1, le=600, description="調理時間（分）")
    ingredients: Optional[str] = Field(None, max_length=1000, description="材料")
    instructions: Optional[str] = Field(None, max_length=2000, description="作り方")
    memo: Optional[str] = Field(None, max_length=500, description="メモ")
    recipe_url: Optional[str] = Field(None, max_length=500, description="レシピURL")
    
    @validator('recipe_url')
    def validate_url(cls, v):
        if v is not None:
            url_pattern = r'^https?://[\w\-._~:/?#[\]@!$&\'()*+,;=%]+$'
            if not re.match(url_pattern, v):
                raise ValueError('有効なURLを入力してください')
        return v
    
    @validator('ingredients', 'instructions', 'memo')
    def sanitize_text_fields(cls, v):
        if v is not None:
            # HTMLタグ除去・サニタイゼーション
            import bleach
            allowed_tags = []  # HTMLタグは一切許可しない
            cleaned = bleach.clean(v, tags=allowed_tags, strip=True)
            return cleaned.strip()
        return v
```

#### 3.1.2 SQLインジェクション対策
```python
# backend/app/crud/base.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Any, Dict, List, Optional

class BaseCRUD:
    def __init__(self, model):
        self.model = model
    
    async def get_by_id(self, db: AsyncSession, id: str) -> Optional[Any]:
        """ID指定取得（パラメータ化クエリ使用）"""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def search_by_name(self, db: AsyncSession, name: str) -> List[Any]:
        """名前検索（フルテキスト検索使用）"""
        # SQLインジェクション対策：パラメータ化クエリ使用
        query = select(self.model).where(
            text("to_tsvector('japanese', name) @@ plainto_tsquery('japanese', :search_term)")
        ).params(search_term=name)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> Any:
        """レコード作成"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
```

### 3.2 ファイルアップロード対策

```python
# backend/app/core/file_security.py
import magic
from PIL import Image
from typing import BinaryIO, Tuple

class FileSecurityManager:
    def __init__(self):
        self.allowed_image_types = ["image/jpeg", "image/png", "image/webp"]
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.max_image_dimension = 2048  # 2048x2048px
    
    def validate_image_upload(self, file: BinaryIO, filename: str) -> Dict[str, Any]:
        """画像ファイル検証"""
        file.seek(0)
        file_content = file.read()
        file.seek(0)
        
        # ファイルサイズチェック
        if len(file_content) > self.max_file_size:
            raise ValueError(f"ファイルサイズが大きすぎます（最大{self.max_file_size // (1024*1024)}MB）")
        
        # MIMEタイプ検証（拡張子偽装対策）
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in self.allowed_image_types:
            raise ValueError(f"許可されていないファイル形式です: {mime_type}")
        
        # 画像として開けるかチェック
        try:
            with Image.open(file) as img:
                # 画像サイズチェック
                width, height = img.size
                if width > self.max_image_dimension or height > self.max_image_dimension:
                    raise ValueError(f"画像サイズが大きすぎます（最大{self.max_image_dimension}x{self.max_image_dimension}px）")
                
                # EXIFデータ除去（個人情報漏洩防止）
                img_without_exif = Image.new(img.mode, img.size)
                img_without_exif.putdata(list(img.getdata()))
                
                return {
                    "is_valid": True,
                    "mime_type": mime_type,
                    "size": (width, height),
                    "processed_image": img_without_exif
                }
                
        except Exception as e:
            raise ValueError(f"画像ファイルが破損しています: {str(e)}")
    
    def generate_secure_filename(self, original_filename: str) -> str:
        """安全なファイル名生成"""
        import uuid
        import os
        
        # 拡張子を取得
        _, ext = os.path.splitext(original_filename)
        
        # UUIDベースの安全なファイル名生成
        secure_name = f"{uuid.uuid4()}{ext.lower()}"
        
        return secure_name
```

---

## 4. データ保護・暗号化

### 4.1 データベース暗号化

#### 4.1.1 機密データの暗号化
```python
# backend/app/core/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    def __init__(self):
        self.master_key = settings.ENCRYPTION_MASTER_KEY.encode()
    
    def _derive_key(self, salt: bytes) -> bytes:
        """暗号化キー導出"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # PBKDF2イテレーション数
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key))
    
    def encrypt_personal_data(self, data: str) -> str:
        """個人情報暗号化"""
        if not data:
            return data
        
        # ランダムソルト生成
        salt = os.urandom(16)
        key = self._derive_key(salt)
        
        # データ暗号化
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode('utf-8'))
        
        # ソルト + 暗号化データを結合
        combined = salt + encrypted_data
        return base64.urlsafe_b64encode(combined).decode('utf-8')
    
    def decrypt_personal_data(self, encrypted_data: str) -> str:
        """個人情報復号化"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            # Base64デコード
            combined = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # ソルトと暗号化データを分離
            salt = combined[:16]
            encrypted = combined[16:]
            
            # キー導出
            key = self._derive_key(salt)
            
            # データ復号化
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            # 復号化エラー時はログ記録してNoneを返す
            logger.error(f"Decryption failed: {str(e)}")
            return None

# SQLAlchemy モデルでの使用例
class User(BaseModel):
    id: str
    email: str
    full_name: str
    phone_encrypted: Optional[str]  # 暗号化フィールド
    address_encrypted: Optional[str]  # 暗号化フィールド
    
    @property
    def phone(self) -> Optional[str]:
        """電話番号復号化"""
        if self.phone_encrypted:
            return encryption_manager.decrypt_personal_data(self.phone_encrypted)
        return None
    
    @phone.setter
    def phone(self, value: Optional[str]):
        """電話番号暗号化"""
        if value:
            self.phone_encrypted = encryption_manager.encrypt_personal_data(value)
        else:
            self.phone_encrypted = None
```

### 4.2 通信暗号化

#### 4.2.1 HTTPS強制設定
```python
# backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# HTTPS強制リダイレクト（本番環境のみ）
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# 信頼できるホストのみ許可
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# セキュリティヘッダー設定
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    # セキュリティヘッダー追加
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    )
    
    return response
```

---

## 5. アクセス制御・権限管理

### 5.1 RBAC（Role-Based Access Control）

#### 5.1.1 権限定義
```python
# backend/app/core/permissions.py
from enum import Enum
from typing import Dict, List, Set

class Permission(Enum):
    # レシピ関連
    RECIPE_READ = "recipe:read"
    RECIPE_CREATE = "recipe:create"
    RECIPE_UPDATE = "recipe:update"
    RECIPE_DELETE = "recipe:delete"
    
    # 献立関連
    MENU_READ = "menu:read"
    MENU_CREATE = "menu:create"
    MENU_UPDATE = "menu:update"
    
    # 作業管理関連
    TASK_READ = "task:read"
    TASK_CREATE = "task:create"
    TASK_UPDATE = "task:update"
    TASK_COMPLETE = "task:complete"
    
    # メッセージ関連
    MESSAGE_READ = "message:read"
    MESSAGE_SEND = "message:send"
    
    # 買い物関連
    SHOPPING_READ = "shopping:read"
    SHOPPING_CREATE = "shopping:create"
    SHOPPING_UPDATE = "shopping:update"
    
    # レポート関連
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    
    # ユーザー管理関連
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DEACTIVATE = "user:deactivate"
    USER_MANAGE = "user:manage"
    
    # アサイン管理関連
    ASSIGNMENT_READ = "assignment:read"
    ASSIGNMENT_CREATE = "assignment:create"
    ASSIGNMENT_UPDATE = "assignment:update"
    ASSIGNMENT_DELETE = "assignment:delete"
    
    # 監査ログ関連
    AUDIT_READ = "audit:read"
    
    # 通知関連
    NOTIFICATION_READ = "notification:read"
    NOTIFICATION_SEND = "notification:send"
    
    # システム設定関連
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"
    
    # CSV関連
    CSV_EXPORT = "csv:export"
    CSV_IMPORT = "csv:import"
    
    # システム管理者権限
    SYSTEM_ADMIN = "system:admin"

class Role(Enum):
    SENIOR = "senior"
    HELPER = "helper"
    CARE_MANAGER = "care_manager"
    SYSTEM_ADMIN = "system_admin"

# ロール別権限マッピング
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SENIOR: {
        Permission.RECIPE_READ,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_UPDATE,
        Permission.RECIPE_DELETE,
        Permission.MENU_READ,
        Permission.MENU_CREATE,
        Permission.MENU_UPDATE,
        Permission.MESSAGE_READ,
        Permission.MESSAGE_SEND,
        Permission.SHOPPING_READ,
    },
    
    Role.HELPER: {
        Permission.RECIPE_READ,
        Permission.MENU_READ,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_COMPLETE,
        Permission.MESSAGE_READ,
        Permission.MESSAGE_SEND,
        Permission.SHOPPING_READ,
        Permission.SHOPPING_CREATE,
        Permission.SHOPPING_UPDATE,
        Permission.REPORT_CREATE,
    },
    
    Role.CARE_MANAGER: {
        Permission.RECIPE_READ,
        Permission.MENU_READ,
        Permission.TASK_READ,
        Permission.MESSAGE_READ,
        Permission.SHOPPING_READ,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
        # 担当範囲内のユーザー閲覧権限
        Permission.USER_READ,
        Permission.ASSIGNMENT_READ,
        # 限定CSV出力権限
        Permission.CSV_EXPORT,
        # 通知受信権限
        Permission.NOTIFICATION_READ,
    },
    
    Role.SYSTEM_ADMIN: set(Permission)  # 全権限
}

class PermissionChecker:
    @staticmethod
    def has_permission(user_role: str, required_permission: Permission) -> bool:
        """権限チェック"""
        try:
            role = Role(user_role)
            return required_permission in ROLE_PERMISSIONS.get(role, set())
        except ValueError:
            return False
    
    @staticmethod
    def check_resource_access(user_role: str, user_id: str, resource_user_id: str, 
                            required_permission: Permission) -> bool:
        """リソースアクセス権限チェック"""
        # 基本権限チェック
        if not PermissionChecker.has_permission(user_role, required_permission):
            return False
        
        # 自分のリソースまたは管理者権限
        if user_id == resource_user_id:
            return True
        
        # ケアマネージャーとシステム管理者は他のユーザーのリソースにアクセス可能
        # ※care_managerはアサインベースのスコープ制限あり（5.1.3参照）
        if user_role in [Role.CARE_MANAGER.value, Role.SYSTEM_ADMIN.value]:
            return True
        
        return False
```

#### 5.1.2 権限デコレーター
```python
# backend/app/core/auth_decorators.py
from functools import wraps
from fastapi import HTTPException, status, Depends
from .permissions import Permission, PermissionChecker

def require_permission(permission: Permission):
    """権限要求デコレーター"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=Depends(get_current_user), **kwargs):
            if not PermissionChecker.has_permission(current_user.role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_resource_access(permission: Permission, resource_user_id_param: str = "user_id"):
    """リソースアクセス権限デコレーター"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=Depends(get_current_user), **kwargs):
            resource_user_id = kwargs.get(resource_user_id_param)
            
            if not PermissionChecker.check_resource_access(
                current_user.role, 
                current_user.id, 
                resource_user_id, 
                permission
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this resource"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# 使用例
@router.get("/recipes/{recipe_id}")
@require_permission(Permission.RECIPE_READ)
async def get_recipe(recipe_id: str, current_user: User = Depends(get_current_user)):
    # レシピ取得処理
    pass

@router.put("/users/{user_id}/profile")
@require_resource_access(Permission.USER_MANAGE, "user_id")
async def update_user_profile(user_id: str, current_user: User = Depends(get_current_user)):
    # ユーザープロフィール更新処理
    pass
```

#### 5.1.3 アサインベースアクセス制御（care_manager用）

care_managerの閲覧権限は`user_assignments`テーブルを基に、担当範囲内のユーザーに制限される。

```python
# backend/app/core/assignment_access.py
from sqlalchemy import select, or_
from app.db.models.user_assignment import UserAssignment

class AssignmentAccessChecker:
    @staticmethod
    async def get_accessible_user_ids(
        db: AsyncSession,
        care_manager_id: str
    ) -> Set[str]:
        """ケアマネージャーがアクセス可能なユーザーIDを取得"""
        query = select(UserAssignment).where(
            UserAssignment.assigned_by == care_manager_id,
            UserAssignment.status == 'active'
        )
        result = await db.execute(query)
        assignments = result.scalars().all()
        
        user_ids = set()
        for assignment in assignments:
            user_ids.add(str(assignment.helper_id))
            user_ids.add(str(assignment.senior_id))
        
        return user_ids
    
    @staticmethod
    async def can_access_user(
        db: AsyncSession,
        care_manager_id: str,
        target_user_id: str
    ) -> bool:
        """ケアマネージャーが特定ユーザーにアクセス可能か判定"""
        accessible = await AssignmentAccessChecker.get_accessible_user_ids(
            db, care_manager_id
        )
        return target_user_id in accessible

def require_assignment_access(resource_user_id_param: str = "user_id"):
    """アサインベースアクセス制御デコレーター（care_manager用）"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=Depends(get_current_user), 
                         db=Depends(get_db), **kwargs):
            # system_adminは無条件アクセス可
            if current_user.role == Role.SYSTEM_ADMIN.value:
                return await func(*args, current_user=current_user, db=db, **kwargs)
            
            # care_managerはアサインベースでスコープ制限
            if current_user.role == Role.CARE_MANAGER.value:
                target_user_id = kwargs.get(resource_user_id_param)
                if target_user_id and not await AssignmentAccessChecker.can_access_user(
                    db, str(current_user.id), target_user_id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="このユーザーへのアクセス権限がありません"
                    )
                return await func(*args, current_user=current_user, db=db, **kwargs)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="管理機能へのアクセス権限がありません"
            )
        return wrapper
    return decorator
```

#### 5.1.4 管理者用セキュリティポリシー

管理機能（`/api/v1/admin/`）には以下の追加セキュリティ対策を適用する:

| ポリシー | 内容 | 対象ロール |
|---------|------|----------|
| **セッションタイムアウト短縮** | 管理セッションは15分（通常30分） | system_admin |
| **初回パスワード変更強制** | 初回ログイン時にパスワード変更を必須化 | system_admin |
| **パスワード定期変更推奨** | 90日ごとの変更を推奨（警告表示） | system_admin |
| **操作監査ログ** | 全管理操作をaudit_logsテーブルに自動記録 | system_admin, care_manager |
| **最終管理者保護** | 最後のアクティブsystem_adminの無効化を禁止 | system_admin |
| **管理APIレート制限** | 500リクエスト/時間（通常1,000） | system_admin, care_manager |
| **2要素認証推奨** | MFA導入を推奨（将来対応） | system_admin |

```python
# 管理操作の監査ログ自動記録ミドルウェア
class AdminAuditMiddleware:
    async def __call__(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/admin/"):
            # リクエスト情報を記録
            audit_data = {
                "user_id": request.state.user.id if hasattr(request.state, 'user') else None,
                "action": f"{request.method} {request.url.path}",
                "resource_type": self._extract_resource_type(request.url.path),
                "metadata": {
                    "ip_address": request.client.host,
                    "user_agent": request.headers.get("user-agent", ""),
                    "method": request.method,
                    "path": request.url.path,
                }
            }
            
            response = await call_next(request)
            
            # レスポンスステータスも記録
            audit_data["metadata"]["status_code"] = response.status_code
            await self._save_audit_log(audit_data)
            
            return response
        
        return await call_next(request)
```

---

## 6. ログ・監査・監視

### 6.1 セキュリティログ

#### 6.1.1 ログ設定
```python
# backend/app/core/logging_config.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # ファイルハンドラー設定
        handler = logging.FileHandler("/app/logs/security.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_auth_attempt(self, email: str, success: bool, ip_address: str, 
                        user_agent: str, failure_reason: str = None):
        """認証試行ログ"""
        log_data = {
            "event": "auth_attempt",
            "email": email,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if not success and failure_reason:
            log_data["failure_reason"] = failure_reason
        
        self.logger.info(json.dumps(log_data))
    
    def log_permission_denied(self, user_id: str, role: str, requested_permission: str, 
                            resource: str, ip_address: str):
        """権限拒否ログ"""
        log_data = {
            "event": "permission_denied",
            "user_id": user_id,
            "role": role,
            "requested_permission": requested_permission,
            "resource": resource,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(json.dumps(log_data))
    
    def log_data_access(self, user_id: str, action: str, resource_type: str, 
                       resource_id: str, ip_address: str):
        """データアクセスログ"""
        log_data = {
            "event": "data_access",
            "user_id": user_id,
            "action": action,  # create, read, update, delete
            "resource_type": resource_type,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_security_incident(self, incident_type: str, description: str, 
                            severity: str, ip_address: str, user_id: str = None):
        """セキュリティインシデントログ"""
        log_data = {
            "event": "security_incident",
            "incident_type": incident_type,
            "description": description,
            "severity": severity,  # low, medium, high, critical
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        self.logger.error(json.dumps(log_data))

security_logger = SecurityLogger()
```

### 6.2 異常検知・アラート

#### 6.2.1 不正アクセス検知
```python
# backend/app/core/security_monitor.py
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Dict, List

class SecurityMonitor:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.failed_login_threshold = 5  # 5回失敗でロック
        self.lockout_duration = 30  # 30分ロック
        self.suspicious_request_threshold = 100  # 100リクエスト/時間
    
    async def check_failed_login_attempts(self, ip_address: str) -> bool:
        """ログイン失敗回数チェック"""
        key = f"failed_login:{ip_address}"
        failed_count = await self.redis_client.get(key)
        
        if failed_count and int(failed_count) >= self.failed_login_threshold:
            return False  # ロック中
        
        return True  # ログイン可能
    
    async def record_failed_login(self, ip_address: str, email: str):
        """ログイン失敗記録"""
        key = f"failed_login:{ip_address}"
        
        # 失敗回数増加
        failed_count = await self.redis_client.incr(key)
        await self.redis_client.expire(key, self.lockout_duration * 60)
        
        # 閾値超過時はアラート
        if failed_count >= self.failed_login_threshold:
            await self._send_security_alert(
                "Multiple failed login attempts",
                f"IP {ip_address} has {failed_count} failed login attempts for {email}",
                "medium"
            )
    
    async def clear_failed_login_attempts(self, ip_address: str):
        """ログイン失敗回数クリア"""
        key = f"failed_login:{ip_address}"
        await self.redis_client.delete(key)
    
    async def check_request_rate(self, ip_address: str) -> bool:
        """リクエスト頻度チェック"""
        key = f"request_rate:{ip_address}"
        current_hour = datetime.utcnow().strftime("%Y%m%d%H")
        hourly_key = f"{key}:{current_hour}"
        
        request_count = await self.redis_client.incr(hourly_key)
        await self.redis_client.expire(hourly_key, 3600)  # 1時間
        
        if request_count > self.suspicious_request_threshold:
            await self._send_security_alert(
                "Suspicious request rate",
                f"IP {ip_address} has made {request_count} requests in the current hour",
                "high"
            )
            return False
        
        return True
    
    async def detect_sql_injection_attempt(self, request_data: str, ip_address: str, 
                                         user_id: str = None):
        """SQLインジェクション検知"""
        sql_injection_patterns = [
            r"union\s+select",
            r"or\s+1\s*=\s*1",
            r"drop\s+table",
            r"exec\s*\(",
            r"script\s*>",
            r"<\s*script"
        ]
        
        import re
        for pattern in sql_injection_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                await self._send_security_alert(
                    "SQL Injection attempt detected",
                    f"Potential SQL injection from IP {ip_address}: {request_data[:100]}",
                    "critical"
                )
                
                security_logger.log_security_incident(
                    "sql_injection_attempt",
                    f"Detected pattern: {pattern}",
                    "critical",
                    ip_address,
                    user_id
                )
                return True
        
        return False
    
    async def _send_security_alert(self, title: str, description: str, severity: str):
        """セキュリティアラート送信"""
        # メール・Slack・Teams等への通知実装
        alert_data = {
            "title": title,
            "description": description,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 重要度が高い場合は即座に通知
        if severity in ["high", "critical"]:
            # 実装例：メール送信、Slack通知など
            pass

security_monitor = SecurityMonitor()
```

### 6.3 個人データアクセス追跡

※ 完全な仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション3を参照

高齢者の個人情報へのアクセスを`data_access_logs`テーブルで追跡する。既存の`SecurityLogger.log_data_access()`を拡張し、**誰が・誰の・どのデータに**アクセスしたかを記録する。

```python
# SecurityLogger への追加メソッド
def log_personal_data_access(self, accessor_user_id: str, accessor_role: str,
                              target_user_id: str, access_type: str,
                              resource_type: str, data_fields: List[str],
                              ip_address: str, has_assignment: bool):
    """個人データアクセスログ（ファイル + DB両方に記録）"""
    log_data = {
        "event": "personal_data_access",
        "accessor_user_id": accessor_user_id,
        "accessor_role": accessor_role,
        "target_user_id": target_user_id,
        "access_type": access_type,
        "resource_type": resource_type,
        "data_fields": data_fields,
        "ip_address": ip_address,
        "has_assignment": has_assignment,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # ファイルログ（Promtail → Loki）
    self.logger.info(json.dumps(log_data))
    
    # DBログ（data_access_logsテーブルへの非同期バッチ書き込み）
    # DataAccessLogger経由で処理
```

**記録対象**: ユーザープロフィール閲覧、医療メモ閲覧、メッセージ閲覧、タスク完了記録閲覧、CSVエクスポート等

### 6.4 セキュリティアラートルール強化

※ 完全な仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション6を参照

既存のSecurityMonitor（6.2節）を以下のルールで拡張する:

| カテゴリ | ルール | 条件 | 重要度 |
|---------|-------|------|-------|
| **ブルートフォース** | 分散攻撃検知 | 同一IPから3+アカウントに失敗/1時間 | Critical |
| **権限昇格** | 権限外アクセス繰返 | 同一ユーザーから5回以上の403/1時間 | High |
| **権限昇格** | 管理者ロール付与 | system_adminロール付与 | Critical |
| **異常データアクセス** | 大量個人情報閲覧 | 1時間以内に50件以上の異なるユーザーデータ | High |
| **異常データアクセス** | 担当外アクセス | has_assignment=falseの個人データアクセス | Medium |
| **異常データアクセス** | 深夜帯アクセス | 22:00-6:00 JSTに個人情報アクセス | Medium |
| **データ持ち出し** | 連続エクスポート | 1日に3回以上のCSVエクスポート | High |
| **セッション異常** | 同時多重ログイン | 同一ユーザーが3+異なるIPからアクティブ | High |
| **ログ完全性** | 改ざん検知 | 日次チェーンハッシュ検証失敗 | Critical |

### 6.5 コンプライアンス要件

※ 完全な仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション5を参照

改正個人情報保護法に基づき、以下のイベントを`compliance_logs`テーブルに記録する:

- **同意管理**: 利用規約・プライバシーポリシーへの同意/撤回
- **データ主体権利行使**: 開示・訂正・削除・利用停止請求と対応結果
- **漏えい対応**: 検知→個人情報保護委員会報告（3〜5日以内）→本人通知→確報（30日以内）
- **データ保持**: 保持期間超過データの自動削除と削除証跡

### 6.6 ログ完全性保証

HMAC-SHA256署名 + 日次チェーンハッシュにより、ログの改ざん・削除を検知する。

- **エントリ単位署名**: 各data_access_logs/compliance_logsエントリにHMAC-SHA256ハッシュを付与
- **日次チェーンハッシュ**: 前日の最終ハッシュを翌日初回に含め、連鎖的に検証
- **検証バッチ**: 毎日03:00 JSTに前日分を自動検証。失敗時はP1アラート発行

### 6.7 集中ログ収集基盤

※ 完全な仕様は[ログ監査・収集強化仕様書](./logging_audit_specification.md) セクション2を参照

**Loki + Promtail**を導入し、分散するログを一元管理する:

- **Promtail**: Dockerコンテナログ + アプリケーションログ + セキュリティログを収集
- **Loki**: ラベルベースインデックスで効率的な保存・検索
- **Grafana**: Lokiデータソースを追加し、ログ検索ダッシュボードを提供
- **共通フィールド**: `trace_id`（リクエスト追跡ID）でサービス横断的なログ追跡が可能

---

## 7. セキュリティテスト

### 7.1 自動化セキュリティテスト

#### 7.1.1 SQLインジェクションテスト
```python
# tests/security/test_sql_injection.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestSQLInjection:
    
    @pytest.mark.parametrize("malicious_input", [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1; EXEC xp_cmdshell('dir'); --",
        "admin'/*",
        "1' UNION SELECT null,username,password FROM users--"
    ])
    def test_sql_injection_protection(self, malicious_input, authenticated_client):
        """SQLインジェクション防御テスト"""
        # レシピ検索でのSQLインジェクション試行
        response = authenticated_client.get(
            f"/api/v1/recipes?search={malicious_input}"
        )
        
        # 400 Bad Request または正常レスポンス（攻撃が無効化される）
        assert response.status_code in [200, 400, 422]
        
        # レスポンスにSQLエラーが含まれていないことを確認
        response_text = response.text.lower()
        sql_error_keywords = ["sql", "syntax error", "mysql", "postgresql", "sqlite"]
        for keyword in sql_error_keywords:
            assert keyword not in response_text
    
    def test_parameterized_queries(self, test_db):
        """パラメータ化クエリのテスト"""
        from app.crud.recipe import recipe_crud
        
        # 正常なケース
        recipes = recipe_crud.search_by_name(test_db, "鶏肉")
        assert isinstance(recipes, list)
        
        # SQLインジェクション試行
        malicious_search = "'; DROP TABLE recipes; --"
        recipes = recipe_crud.search_by_name(test_db, malicious_search)
        
        # テーブルが削除されていないことを確認
        all_recipes = recipe_crud.get_all(test_db)
        assert isinstance(all_recipes, list)
```

#### 7.1.2 XSS脆弱性テスト
```python
# tests/security/test_xss.py
import pytest
from fastapi.testclient import TestClient

class TestXSSProtection:
    
    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "';alert('XSS');//"
    ])
    def test_xss_protection_in_recipe_creation(self, xss_payload, authenticated_client):
        """レシピ作成でのXSS防御テスト"""
        recipe_data = {
            "name": f"テストレシピ{xss_payload}",
            "category": "和食",
            "type": "主菜",
            "difficulty": "普通",
            "cooking_time": 30,
            "ingredients": f"材料リスト{xss_payload}",
            "instructions": f"作り方{xss_payload}"
        }
        
        response = authenticated_client.post("/api/v1/recipes", json=recipe_data)
        
        if response.status_code == 201:
            # 作成成功の場合、レスポンスにスクリプトタグが含まれていないことを確認
            recipe = response.json()
            for field in ["name", "ingredients", "instructions"]:
                if field in recipe:
                    assert "<script>" not in recipe[field].lower()
                    assert "javascript:" not in recipe[field].lower()
                    assert "onerror=" not in recipe[field].lower()
    
    def test_content_security_policy_headers(self, client):
        """CSPヘッダーの確認"""
        response = client.get("/api/v1/health")
        
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        
        # 基本的なCSPディレクティブの確認
        assert "default-src 'self'" in csp
        assert "script-src" in csp
```

### 7.2 脆弱性スキャン

#### 7.2.1 自動脆弱性スキャン
```python
# security/vulnerability_scanner.py
import subprocess
import json
from typing import Dict, List

class VulnerabilityScanner:
    
    def scan_dependencies(self) -> Dict[str, Any]:
        """依存関係の脆弱性スキャン"""
        try:
            # Python依存関係スキャン（safety使用）
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd="/app"
            )
            
            if result.stdout:
                vulnerabilities = json.loads(result.stdout)
                return {
                    "status": "completed",
                    "vulnerabilities": vulnerabilities,
                    "total_count": len(vulnerabilities)
                }
            else:
                return {
                    "status": "completed", 
                    "vulnerabilities": [],
                    "total_count": 0
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def scan_docker_image(self, image_name: str) -> Dict[str, Any]:
        """Dockerイメージの脆弱性スキャン"""
        try:
            # Trivyを使用したスキャン
            result = subprocess.run(
                ["trivy", "image", "--format", "json", image_name],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                scan_result = json.loads(result.stdout)
                return {
                    "status": "completed",
                    "scan_result": scan_result
                }
            else:
                return {
                    "status": "no_vulnerabilities"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def generate_security_report(self) -> Dict[str, Any]:
        """セキュリティレポート生成"""
        dependency_scan = self.scan_dependencies()
        docker_scan = self.scan_docker_image("helper-system:latest")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "dependency_vulnerabilities": dependency_scan,
            "docker_vulnerabilities": docker_scan,
            "recommendations": self._generate_recommendations(dependency_scan, docker_scan)
        }
    
    def _generate_recommendations(self, dep_scan: Dict, docker_scan: Dict) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        if dep_scan.get("total_count", 0) > 0:
            recommendations.append("依存関係の脆弱性が検出されました。パッケージの更新を検討してください。")
        
        if docker_scan.get("status") == "completed":
            recommendations.append("Dockerイメージのセキュリティスキャンを定期的に実行してください。")
        
        return recommendations
```

---

## 8. 運用セキュリティ

### 8.1 セキュリティ監視

#### 8.1.1 リアルタイム監視
```python
# backend/app/core/security_dashboard.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

class SecurityDashboard:
    
    async def get_security_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """セキュリティメトリクス取得"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        return {
            "failed_login_attempts": await self._count_failed_logins(start_time, end_time),
            "blocked_ips": await self._get_blocked_ips(),
            "suspicious_requests": await self._count_suspicious_requests(start_time, end_time),
            "active_sessions": await self._count_active_sessions(),
            "recent_security_incidents": await self._get_recent_incidents(start_time, end_time)
        }
    
    async def _count_failed_logins(self, start_time: datetime, end_time: datetime) -> int:
        """ログイン失敗回数集計"""
        # ログファイルまたはデータベースから集計
        return 0  # 実装例
    
    async def _get_blocked_ips(self) -> List[str]:
        """ブロック中IPアドレス一覧"""
        blocked_ips = []
        
        # Redisからブロック中IPを取得
        pattern = "failed_login:*"
        keys = await security_monitor.redis_client.keys(pattern)
        
        for key in keys:
            count = await security_monitor.redis_client.get(key)
            if count and int(count) >= security_monitor.failed_login_threshold:
                ip = key.decode().split(":")[1]
                blocked_ips.append(ip)
        
        return blocked_ips
    
    async def health_check_security(self) -> Dict[str, Any]:
        """セキュリティヘルスチェック"""
        checks = {
            "ssl_certificate": await self._check_ssl_certificate(),
            "security_headers": await self._check_security_headers(),
            "database_connection": await self._check_database_security(),
            "redis_connection": await self._check_redis_security()
        }
        
        all_healthy = all(check["status"] == "healthy" for check in checks.values())
        
        return {
            "overall_status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "last_updated": datetime.utcnow().isoformat()
        }
```

### 8.2 インシデント対応

#### 8.2.1 自動対応システム
```python
# backend/app/core/incident_response.py
from enum import Enum

class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentResponse:
    
    async def handle_security_incident(self, incident_type: str, severity: IncidentSeverity, 
                                     details: Dict[str, Any]):
        """セキュリティインシデント自動対応"""
        
        # ログ記録
        security_logger.log_security_incident(
            incident_type, 
            details.get("description", ""), 
            severity.value,
            details.get("ip_address", ""),
            details.get("user_id")
        )
        
        # 重要度別対応
        if severity == IncidentSeverity.CRITICAL:
            await self._critical_incident_response(incident_type, details)
        elif severity == IncidentSeverity.HIGH:
            await self._high_incident_response(incident_type, details)
        elif severity == IncidentSeverity.MEDIUM:
            await self._medium_incident_response(incident_type, details)
    
    async def _critical_incident_response(self, incident_type: str, details: Dict[str, Any]):
        """緊急対応"""
        # 1. 即座にアラート送信
        await self._send_emergency_alert(incident_type, details)
        
        # 2. 該当IPアドレスの即座ブロック
        if "ip_address" in details:
            await self._block_ip_address(details["ip_address"])
        
        # 3. 該当ユーザーのセッション無効化
        if "user_id" in details:
            await self._revoke_user_sessions(details["user_id"])
        
        # 4. システム管理者への緊急通知
        await self._notify_system_admin(incident_type, details, "CRITICAL")
    
    async def _high_incident_response(self, incident_type: str, details: Dict[str, Any]):
        """高優先度対応"""
        # 1. アラート送信
        await security_monitor._send_security_alert(
            f"High severity incident: {incident_type}",
            details.get("description", ""),
            "high"
        )
        
        # 2. 追加監視開始
        if "ip_address" in details:
            await self._increase_monitoring(details["ip_address"])
    
    async def _block_ip_address(self, ip_address: str, duration: int = 3600):
        """IPアドレスブロック"""
        # Redisにブロック情報保存
        await security_monitor.redis_client.setex(
            f"blocked_ip:{ip_address}", 
            duration, 
            "blocked"
        )
        
        # Web Application Firewall（WAF）への登録
        # 実装はインフラに依存
    
    async def _revoke_user_sessions(self, user_id: str):
        """ユーザーセッション無効化"""
        # 該当ユーザーの全セッション削除
        pattern = f"session:*"
        sessions = await security_monitor.redis_client.keys(pattern)
        
        for session_key in sessions:
            session_data = await security_monitor.redis_client.get(session_key)
            if session_data:
                session_info = json.loads(session_data)
                if session_info.get("user_id") == user_id:
                    await security_monitor.redis_client.delete(session_key)
```

---

## 9. コンプライアンス・監査対応

### 9.1 監査ログ

#### 9.1.1 詳細監査ログ
```python
# backend/app/core/audit_logger.py
import json
from datetime import datetime
from typing import Dict, Any, Optional

class AuditLogger:
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        handler = logging.FileHandler("/app/logs/audit.log")
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_data_access(self, user_id: str, action: str, resource_type: str, 
                       resource_id: str, before_data: Optional[Dict] = None,
                       after_data: Optional[Dict] = None, ip_address: str = None):
        """データアクセス監査ログ"""
        
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "data_access",
            "user_id": user_id,
            "action": action,  # create, read, update, delete
            "resource": {
                "type": resource_type,
                "id": resource_id
            },
            "ip_address": ip_address,
            "session_id": self._get_session_id(),
        }
        
        # 変更データの記録（個人情報は除く）
        if action in ["update", "delete"] and before_data:
            audit_record["before_data"] = self._sanitize_data(before_data)
        
        if action in ["create", "update"] and after_data:
            audit_record["after_data"] = self._sanitize_data(after_data)
        
        self.logger.info(json.dumps(audit_record))
    
    def log_system_access(self, user_id: str, action: str, details: Dict[str, Any]):
        """システムアクセス監査ログ"""
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "system_access",
            "user_id": user_id,
            "action": action,  # login, logout, password_change, etc.
            "details": details
        }
        
        self.logger.info(json.dumps(audit_record))
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """個人情報のマスキング"""
        sanitized = data.copy()
        
        # マスキング対象フィールド
        sensitive_fields = ["password", "phone", "address", "medical_notes"]
        
        for field in sensitive_fields:
            if field in sanitized:
                if sanitized[field]:
                    sanitized[field] = "*" * len(str(sanitized[field]))
        
        return sanitized

audit_logger = AuditLogger()
```

### 9.2 個人情報保護対応

#### 9.2.1 データ削除・匿名化
```python
# backend/app/core/data_protection.py
class DataProtectionManager:
    
    async def anonymize_user_data(self, user_id: str) -> Dict[str, Any]:
        """利用者データの匿名化"""
        # 1. 個人識別情報の削除・匿名化
        anonymized_data = {
            "user_id": f"anonymous_{secrets.token_hex(8)}",
            "full_name": "匿名ユーザー",
            "email": f"anonymous_{secrets.token_hex(8)}@example.com",
            "phone": None,
            "address": None,
            "emergency_contact": None,
            "medical_notes": None
        }
        
        # 2. 関連データの匿名化
        await self._anonymize_related_data(user_id, anonymized_data["user_id"])
        
        # 3. 監査ログ記録
        audit_logger.log_data_access(
            user_id=user_id,
            action="anonymize",
            resource_type="user",
            resource_id=user_id
        )
        
        return anonymized_data
    
    async def delete_user_data(self, user_id: str, retention_period_expired: bool = False):
        """利用者データの完全削除"""
        if not retention_period_expired:
            # 保持期間確認
            user = await self._get_user(user_id)
            if user and not self._is_retention_period_expired(user.created_at):
                raise ValueError("データ保持期間中のため削除できません")
        
        # 1. 関連データの削除
        await self._delete_user_recipes(user_id)
        await self._delete_user_menus(user_id)
        await self._delete_user_messages(user_id)
        await self._delete_user_tasks(user_id)
        
        # 2. ユーザーデータの削除
        await self._delete_user_record(user_id)
        
        # 3. セッション無効化
        await self._revoke_all_user_sessions(user_id)
        
        # 4. 監査ログ記録
        audit_logger.log_data_access(
            user_id=user_id,
            action="delete",
            resource_type="user",
            resource_id=user_id
        )
    
    def _is_retention_period_expired(self, created_at: datetime) -> bool:
        """データ保持期間の確認"""
        retention_period = timedelta(days=365 * 3)  # 3年間
        return datetime.utcnow() - created_at > retention_period
```

---

## 10. 実装チェックリスト

### 10.1 認証・認可
- [ ] JWT実装（アクセス・リフレッシュトークン）
- [ ] パスワードハッシュ化（bcrypt）
- [ ] QRコード認証システム
- [ ] セッション管理（Redis）
- [ ] RBAC実装
- [ ] 権限チェック機能

### 10.2 データ保護
- [ ] 個人情報暗号化
- [ ] HTTPS強制設定
- [ ] セキュリティヘッダー設定
- [ ] 入力検証・サニタイゼーション
- [ ] SQLインジェクション対策
- [ ] XSS対策

### 10.3 監視・ログ
- [ ] セキュリティログ実装
- [ ] 監査ログ実装
- [ ] 異常検知システム
- [ ] 自動アラート機能
- [ ] インシデント対応システム

### 10.4 テスト・監査
- [ ] セキュリティテスト実装
- [ ] 脆弱性スキャン設定
- [ ] 監査対応機能
- [ ] データ削除・匿名化機能
- [ ] コンプライアンス確認

---

**文書終了**