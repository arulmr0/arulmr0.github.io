from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError, ValidationError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Role, User
from app.schemas.auth import PasswordChange, PasswordReset, UserCreate, UserUpdate


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


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def _active_admin_count(db: Session) -> int:
    return len(
        list(db.scalars(select(User.id).where(User.role == Role.ADMIN, User.is_active.is_(True))))
    )


def update_user(db: Session, user_id: int, data: UserUpdate, acting_user: User) -> User:
    """Change name, role or active flag. The last active admin cannot be demoted or disabled."""
    user = get_user(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    loses_admin = (
        user.role == Role.ADMIN
        and user.is_active
        and (
            changes.get("role", user.role) != Role.ADMIN or changes.get("is_active", True) is False
        )
    )
    if loses_admin and _active_admin_count(db) <= 1:
        raise ValidationError("Cannot remove the last active administrator")
    if user.id == acting_user.id and changes.get("is_active", True) is False:
        raise ValidationError("You cannot deactivate your own account")
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    return user


def reset_password(db: Session, user_id: int, data: PasswordReset) -> User:
    user = get_user(db, user_id)
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> User:
    if not verify_password(data.current_password, user.hashed_password):
        raise ValidationError("Current password is incorrect")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return user
