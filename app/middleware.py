from fastapi import Depends, HTTPException, status
from app import models, auth
from sqlalchemy.orm import Session
from app.database import get_db

# Dependency to verify subscription
def verify_subscription(db: Session = Depends(get_db), current_user = Depends(auth.get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_user.username).first()
    if not user.is_subscribed or user.subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required to access this feature"
        )
    return current_user