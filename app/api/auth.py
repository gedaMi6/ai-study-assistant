import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import aiosmtplib
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from app.database.database import get_connection


load_dotenv()

from app.database.database import get_connection


router = APIRouter(prefix="/auth", tags=["Authentication"])


SESSION_COOKIE = "study_assistant_session"


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
    )

    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=16384,
            r=8,
            p=1,
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except (ValueError, TypeError):
        return False


def hash_reset_code(code: str) -> str:
    return hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()


async def send_password_reset_email(
    email: str,
    code: str
):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_username or not smtp_password:
        raise RuntimeError(
            "SMTP_USERNAME and SMTP_PASSWORD are not configured."
        )

    message = EmailMessage()

    message["From"] = smtp_username
    message["To"] = email
    message["Subject"] = "AI STUDY ASSISTANT Password Reset Code"

    message.set_content(
        f"""AI STUDY ASSISTANT Password Reset

Your password reset code is:

{code}

This code expires in 15 minutes.

If you did not request a password reset, you can safely ignore this email.

AI STUDY ASSISTANT
"""
    )

    await aiosmtplib.send(
        message,
        hostname=smtp_host,
        port=smtp_port,
        use_tls=True,
        username=smtp_username,
        password=smtp_password,
    )


def get_valid_reset_token(
    email: str,
    code: str
):
    connection = get_connection()

    user = connection.execute(
        """
        SELECT id, email
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if not user:
        connection.close()
        return None, None

    code_hash = hash_reset_code(code)

    token = connection.execute(
        """
        SELECT id
        FROM password_reset_tokens
        WHERE user_id = ?
          AND token_hash = ?
          AND used = 0
          AND expires_at > CURRENT_TIMESTAMP
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            user["id"],
            code_hash,
        ),
    ).fetchone()

    connection.close()

    return user, token


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest
):
    email = data.email.strip().lower()

    connection = get_connection()

    user = connection.execute(
        """
        SELECT id, email
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if user:
        # Invalidate any previous reset codes.
        connection.execute(
            """
            UPDATE password_reset_tokens
            SET used = 1
            WHERE user_id = ?
              AND used = 0
            """,
            (user["id"],),
        )

        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = hash_reset_code(code)

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=15)
        ).strftime("%Y-%m-%d %H:%M:%S")

        connection.execute(
            """
            INSERT INTO password_reset_tokens (
                user_id,
                token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (
                user["id"],
                code_hash,
                expires_at,
            ),
        )

        connection.commit()
        connection.close()

        try:
            await send_password_reset_email(
                email,
                code
            )
        except Exception as error:
            print(
                "Password reset email error:",
                error
            )

    else:
        connection.close()

    # Do not reveal whether an account exists.
    return {
        "status": "success",
        "message": (
            "If an account exists for that email, "
            "a password reset code has been sent."
        ),
    }


@router.post("/verify-reset-code")
def verify_reset_code(
    data: VerifyResetCodeRequest
):
    email = data.email.strip().lower()
    code = data.code.strip()

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Enter the 6-digit reset code."
        )

    user, token = get_valid_reset_token(
        email,
        code
    )

    if not user or not token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )

    return {
        "status": "success",
        "message": "Reset code verified successfully.",
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest
):
    email = data.email.strip().lower()
    code = data.code.strip()
    new_password = data.new_password

    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters."
        )

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Enter the 6-digit reset code."
        )

    user, token = get_valid_reset_token(
        email,
        code
    )

    if not user or not token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )

    connection = get_connection()

    password_hash = hash_password(new_password)

    connection.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE id = ?
        """,
        (
            password_hash,
            user["id"],
        ),
    )

    connection.execute(
        """
        UPDATE password_reset_tokens
        SET used = 1
        WHERE id = ?
        """,
        (token["id"],),
    )

    # Force all existing login sessions to expire.
    connection.execute(
        """
        DELETE FROM sessions
        WHERE user_id = ?
        """,
        (user["id"],),
    )

    connection.commit()
    connection.close()

    return {
        "status": "success",
        "message": (
            "Password reset successfully. "
            "Please log in with your new password."
        ),
    }


def get_current_user(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)

    if not session_id:
        return None

    connection = get_connection()

    user = connection.execute(
        """
        SELECT
            users.id,
            users.name,
            users.email,
            users.role,
            users.profile_image,
            users.sidebar_collapsed
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.id = ?
        """,
        (session_id,),
    ).fetchone()

    connection.close()

    return user


@router.post("/register")
def register(data: RegisterRequest, response: Response):

    name = data.name.strip()
    email = data.email.strip().lower()
    password = data.password

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name must contain at least 2 characters."
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters."
        )

    connection = get_connection()

    existing = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if existing:
        connection.close()

        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists."
        )

    password_hash = hash_password(password)

    cursor = connection.execute(
        """
        INSERT INTO users (
            name,
            email,
            password_hash
        )
        VALUES (?, ?, ?)
        """,
        (
            name,
            email,
            password_hash,
        ),
    )

    user_id = cursor.lastrowid

    session_id = secrets.token_urlsafe(32)

    connection.execute(
        """
        INSERT INTO sessions (
            id,
            user_id
        )
        VALUES (?, ?)
        """,
        (
            session_id,
            user_id,
        ),
    )

    connection.commit()
    connection.close()

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
    )

    return {
        "status": "success",
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
        },
    }

@router.post("/login")
def login(data: LoginRequest, response: Response):

    email = data.email.strip().lower()

    connection = get_connection()

    user = connection.execute(
        """
        SELECT
            id,
            name,
            email,
            password_hash,
            role,
            profile_image,
            sidebar_collapsed
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if not user:
        connection.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(
        data.password,
        user["password_hash"]
    ):
        connection.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    session_id = secrets.token_urlsafe(32)

    connection.execute(
        """
        INSERT INTO sessions (
            id,
            user_id
        )
        VALUES (?, ?)
        """,
        (
            session_id,
            user["id"],
        ),
    )

    connection.commit()
    connection.close()

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
    )

    return {
        "status": "success",
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "sidebar_collapsed": bool(user["sidebar_collapsed"]),
            "profile_image": (
                f"/profile/image/{user['profile_image']}"
                if user["profile_image"]
                else None
            ),
        },
    }


@router.post("/logout")
def logout(request: Request, response: Response):

    session_id = request.cookies.get(SESSION_COOKIE)

    if session_id:
        connection = get_connection()

        connection.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )

        connection.commit()
        connection.close()

    response.delete_cookie(SESSION_COOKIE)

    return {
        "status": "success",
        "message": "Logged out successfully."
    }


@router.get("/me")
def me(request: Request):

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    return {
        "status": "success",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "sidebar_collapsed": bool(user["sidebar_collapsed"]),
            "profile_image": (
                f"/profile/image/{user['profile_image']}"
                if user["profile_image"]
                else None
            ),
        },
    }
class SidebarPreferenceRequest(BaseModel):
    collapsed: bool


@router.patch("/sidebar")
def update_sidebar_preference(
    data: SidebarPreferenceRequest,
    request: Request
):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    connection = get_connection()

    connection.execute(
        """
        UPDATE users
        SET sidebar_collapsed = ?
        WHERE id = ?
        """,
        (
            1 if data.collapsed else 0,
            user["id"],
        ),
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT sidebar_collapsed
        FROM users
        WHERE id = ?
        """,
        (user["id"],),
    ).fetchone()

    connection.close()

    return {
        "status": "success",
        "sidebar_collapsed": bool(row["sidebar_collapsed"]),
    }
