import os
import psycopg2
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

SECRET_KEY = (
    os.getenv("APP_JWT_SECRET")
    or os.getenv("JWT_SECRET", "legal-rag-super-secret-key-2024-must-be-32-chars")
)
ALGORITHM  = "HS256"
PG_CONN    = os.getenv("POSTGRES_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb")

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Xác thực JWT và trả về dict {user_id, email, role}.
    - Spring Boot forward Authorization header → FastAPI decode lại.
    - Role được look-up từ PostgreSQL (JWT không chứa role).
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email   = payload.get("email", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
    except JWTError as e:
        print(f"JWT Decode Error: {e}, SECRET_KEY={SECRET_KEY[:8]}...")
        print(f"RECEIVED TOKEN: {token}")
        # FALLBACK: Try the default secret from application.yml in case Spring Boot missed the env var
        try:
            payload = jwt.decode(token, "legal-rag-super-secret-key-2024-must-be-32-chars", algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            email = payload.get("email")
            if user_id is None or email is None:
                raise HTTPException(status_code=401, detail="Token không hợp lệ (fallback thiếu sub/email)")
            print("WARNING: Token decoded using FALLBACK DEFAULT SECRET! Spring Boot is not using APP_JWT_SECRET!")
        except JWTError as e2:
            raise HTTPException(status_code=401, detail=f"Token không hợp lệ: {str(e)} (fallback failed: {str(e2)})")

    # Look-up role từ DB
    role = "user"
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            role = row[0] or "user"
    except Exception:
        pass  # Nếu DB lỗi, giữ role mặc định "user"

    return {"user_id": user_id, "email": email, "role": role}


def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Dependency: chỉ cho phép user có role = 'admin'."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới có quyền thực hiện thao tác này",
        )
    return current_user
