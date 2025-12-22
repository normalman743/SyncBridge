from datetime import datetime
from sqlalchemy.orm import Session

from app.models import License, User


def get_by_key(db: Session, key: str) -> License | None:
    return db.query(License).filter(License.license_key == key).first()


def get_by_user(db: Session, user_id: int) -> License | None:
    return (
        db.query(License)
        .filter(License.user_id == user_id)
        .order_by(License.activated_at.desc().nullslast())
        .first()
    )


def _activate_license(db: Session, lic: License, user: User):
    now = datetime.utcnow()
    lic.status = "active"
    lic.user_id = user.id
    lic.activated_at = now

    user.role = lic.role
    user.is_active = 1
    user.updated_at = now

    db.commit()
    db.refresh(user)
    db.refresh(lic)
    return lic


def activate(db: Session, license_key: str, user: User):
    """
    Activate a license and bind it to the user.
    Returns tuple: (license_row, error_message)
    """
    lic = get_by_key(db, license_key)
    if not lic:
        return None, "License not found"

    if lic.status != "unused":
        return None, "License not unused"

    lic = _activate_license(db, lic, user)
    return lic, None


def activate_new_for_user(db: Session, license_key: str, user: User):
    """
    Activate a new license for user, revoking any existing one.
    Returns tuple: (license_row, error_message)
    """
    lic = get_by_key(db, license_key)
    if not lic:
        return None, "License not found"
    if lic.status != "unused":
        return None, "License not unused"

    current = get_by_user(db, user.id)
    if current and current.status == "active":
        current.status = "revoked"

    lic = _activate_license(db, lic, user)
    return lic, None


def validate_active(db: Session, user: User):
    lic = get_by_user(db, user.id)
    if not lic:
        return None, "License not found"
    if lic.status != "active":
        return None, "License not active"
    if lic.expires_at and lic.expires_at <= datetime.utcnow():
        return None, "License expired"
    return lic, None
