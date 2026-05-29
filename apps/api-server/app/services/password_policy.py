from fastapi import HTTPException, status

from app.core.security import verify_password


PASSWORD_POLICY_MESSAGE = "密码需为 8–20 位，并至少包含大写字母、小写字母、数字、特殊字符中的 3 类。"
PASSWORD_UNCHANGED_MESSAGE = "新密码不能与当前密码相同。"


def password_class_count(password: str) -> int:
    checks = [
        any("A" <= char <= "Z" for char in password),
        any("a" <= char <= "z" for char in password),
        any("0" <= char <= "9" for char in password),
        any(not ("A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9") for char in password),
    ]
    return sum(1 for matched in checks if matched)


def validate_password_policy(password: str) -> None:
    if len(password) < 8 or len(password) > 20 or password_class_count(password) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_POLICY_MESSAGE)


def ensure_password_not_current(new_password: str, current_password_hash: str) -> None:
    if verify_password(new_password, current_password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_UNCHANGED_MESSAGE)
