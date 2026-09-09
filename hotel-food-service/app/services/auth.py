from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate


def create_user(db: Session, data: UserCreate) -> User:
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise ConflictError(f"A user with email {data.email} already exists")
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> str:
    """Return a JWT for valid credentials; raise ``DomainError`` (401) otherwise."""
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        err = DomainError("Invalid email or password")
        err.status_code = 401
        raise err
    return create_access_token(subject=str(user.id), role=user.role.value)


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))
