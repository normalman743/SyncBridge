from datetime import datetime
from sqlalchemy.orm import Session

from app.models import License, User


def get_by_key(db: Session, key: str) -> License | None:
    return db.query(License).filter(License.license_key == key).first()


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

    lic.status = "active"
    lic.user_id = user.id
    lic.activated_at = datetime.utcnow()

    user.role = lic.role
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)
    db.refresh(lic)
    return lic, None
