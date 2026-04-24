import os
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

SECRET_KEY = os.getenv("JWT_SECRET", "legal-rag-super-secret-key-2024-must-be-32-chars")
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)  # auto_error=False → không throw 403 khi missing header


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Xác thực JWT.
    - Spring Boot forward Authorization header → FastAPI decode lại.
    - Nếu không có token → raise 401 (không phải 403).
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
        return user_id
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token không hợp lệ: {str(e)}")
