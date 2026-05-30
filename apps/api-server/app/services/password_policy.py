from fastapi import HTTPException, status

from app.core.security import verify_password


PASSWORD_POLICY_MESSAGE = "密码需为 8–20 位，并至少包含大写字母、小写字母、数字、特殊字符中的 3 类。"
PASSWORD_COMMON_MESSAGE = "密码不能使用常见弱密码。"
PASSWORD_ACCOUNT_SIMILAR_MESSAGE = "密码不能与用户名、邮箱或手机号等账号信息明显相似。"
PASSWORD_UNCHANGED_MESSAGE = "新密码不能与当前密码相同。"
COMMON_WEAK_PASSWORDS = {
    "12345678",
    "123456789",
    "1234567890",
    "abc123456",
    "admin123",
    "change123",
    "changeme",
    "changeme123",
    "huairou123",
    "passw0rd",
    "password",
    "password123",
    "portal123",
    "qwerty123",
}


def password_class_count(password: str) -> int:
    checks = [
        any("A" <= char <= "Z" for char in password),
        any("a" <= char <= "z" for char in password),
        any("0" <= char <= "9" for char in password),
        any(not ("A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9") for char in password),
    ]
    return sum(1 for matched in checks if matched)


def normalize_similarity_token(value: str | None) -> str:
    if not value:
        return ""
    return "".join(char.lower() for char in value.strip() if char.isalnum())


def password_contains_token(password: str, token: str, *, min_length: int = 5) -> bool:
    normalized_password = normalize_similarity_token(password)
    return len(token) >= min_length and token in normalized_password


def password_is_similar_to_account(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
    mobile: str | None = None,
) -> bool:
    username_token = normalize_similarity_token(username)
    if password_contains_token(password, username_token):
        return True

    email_local = (email or "").split("@", maxsplit=1)[0]
    email_token = normalize_similarity_token(email_local)
    if password_contains_token(password, email_token):
        return True

    mobile_digits = "".join(char for char in (mobile or "") if char.isdigit())
    normalized_password = normalize_similarity_token(password)
    if len(mobile_digits) >= 7 and mobile_digits in normalized_password:
        return True
    mobile_tail = mobile_digits[-4:]
    return len(mobile_tail) == 4 and mobile_tail in normalized_password and len(password) <= 12


def validate_password_policy(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
    mobile: str | None = None,
) -> None:
    if len(password) < 8 or len(password) > 20 or password_class_count(password) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_POLICY_MESSAGE)
    if password.lower() in COMMON_WEAK_PASSWORDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_COMMON_MESSAGE)
    if password_is_similar_to_account(password, username=username, email=email, mobile=mobile):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_ACCOUNT_SIMILAR_MESSAGE)


def ensure_password_not_current(new_password: str, current_password_hash: str) -> None:
    if verify_password(new_password, current_password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_UNCHANGED_MESSAGE)
