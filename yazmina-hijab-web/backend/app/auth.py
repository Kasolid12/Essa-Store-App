"""
Yazmina Hijab Web — Authentication (JWT + httpOnly cookie).

Single-admin auth: one username/password stored hashed in admin_users table.
JWT token is set as httpOnly cookie (safe from XSS).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models.admin_user import AdminUser

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


COOKIE_NAME = "yazmina_token"


# ── Helpers ───────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(COOKIE_NAME)


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    """Dependency: verify JWT from cookie, return AdminUser or 401."""
    token = _get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin


# ── Routes ────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate admin and set JWT cookie."""
    admin = db.query(AdminUser).filter(AdminUser.username == body.username).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Username atau password salah")

    # Update last_login
    admin.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": admin.username})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,    # Set True in production (HTTPS)
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )
    return {"message": "Login sukses", "username": admin.username}


@router.post("/logout")
def logout(response: Response):
    """Clear JWT cookie."""
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Logout sukses"}


@router.get("/me")
def get_me(admin: AdminUser = Depends(get_current_admin)):
    """Return current admin info (validates token)."""
    return {"username": admin.username, "last_login": str(admin.last_login) if admin.last_login else None}
