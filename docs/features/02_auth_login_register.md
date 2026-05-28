# 02 · Đăng nhập & Đăng ký

**Route:** `/login`, `/register`
**File backend chính:** `spring-boot/orchestration-service/src/main/java/.../AuthController.java`
**File xác thực FastAPI:** `backend-python/auth/jwt_verify.py`

---

Hệ thống xác thực người dùng dựa trên **JWT (JSON Web Token)**. Spring Boot cấp phát và ký token. FastAPI tự xác thực token đó độc lập, không cần gọi ngược về Spring Boot.

## Luồng đăng nhập

Người dùng nhập email và mật khẩu, frontend gọi `POST /api/auth/login` đến Spring Boot. Spring Boot tra cứu trong PostgreSQL, kiểm tra mật khẩu đã hash bằng BCrypt. Nếu đúng, nó tạo JWT ký bằng HS256 với secret key và trả về cho frontend. Frontend lưu token vào `localStorage`, Axios Interceptor tự động gắn vào mọi request tiếp theo: `Authorization: Bearer <token>`. Sau đó người dùng được chuyển đến `/chat`.

## Luồng đăng ký

Người dùng điền email, mật khẩu và xác nhận mật khẩu. Frontend validate client-side (hai mật khẩu phải khớp, đủ độ dài), rồi gọi `POST /api/auth/register`. Spring Boot hash mật khẩu và tạo tài khoản mới trong PostgreSQL với role mặc định là `user`. Sau đó redirect về trang đăng nhập.

## Điểm kỹ thuật quan trọng: Shared Secret JWT

FastAPI và Spring Boot dùng **cùng một secret key** (biến `JWT_SECRET` trong `.env`). Khi request đến FastAPI, nó tự decode JWT bằng key đó — không cần gọi HTTP sang Spring Boot để hỏi "token này có hợp lệ không". Cách này loại bỏ một network round-trip và tránh tạo dependency vòng giữa hai backend.

Code trong `backend-python/auth/jwt_verify.py`:

```python
SECRET_KEY = os.getenv("JWT_SECRET", "legal-rag-super-secret-key-2024-must-be-32-chars")
ALGORITHM  = "HS256"

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # tự decode, không cần gọi Spring Boot
    user_id = payload.get("sub")
    # Sau khi decode xong → tra PostgreSQL để lấy role hiện tại
    cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
```

**Tại sao không nhúng role vào token?** Vì role có thể thay đổi (admin hạ cấp user). Nếu role nằm trong token, phải chờ token hết hạn mới cập nhật được. Tra PostgreSQL mỗi request đảm bảo role luôn đúng tại thời điểm thực tế.

## Phân quyền

Endpoint `/admin/*` dùng dependency `require_admin` — nếu đúng token nhưng role là `user`, FastAPI trả 403:

```python
# auth/jwt_verify.py
def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện thao tác này")
    return current_user
```

Ở phía frontend, Vue Router cũng kiểm tra role trước khi cho vào trang `/admin` — đây là lớp UX, không phải lớp bảo mật (bảo mật thực sự ở FastAPI).

---

**API chính:** `POST /api/auth/login` — `POST /api/auth/register`
