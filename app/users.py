from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import models, auth, database
from app.models import UserCreate, UserRead
from app.dependencies import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_verification_email(email: str, token: str):
    # Load SMTP credentials from .env
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = smtp_user
    to_email = email
    subject = "Verify your email"
    # Get the API domain from environment variable
    api_domain = os.getenv("API_DOMAIN", "https://yourdomain.com")  # Default value if not set
    verify_link = f"{api_domain}/users/verify?token={token}"
    body = f"Please verify your email by clicking the following link: {verify_link}"
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send verification email: {e}")

@router.post("/register", response_model=UserRead)
def register_user(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    verification_token = secrets.token_urlsafe(32)
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_verified=False,
        verification_token=verification_token
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Send verification email in background
    background_tasks.add_task(send_verification_email, user.email, verification_token)
    return new_user

@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully"}

@router.post("/loging")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_verified:
        # Resend verification email
        verification_token = secrets.token_urlsafe(32)
        user.verification_token = verification_token
        db.commit()
        background_tasks = BackgroundTasks()  # Create a BackgroundTasks instance
        background_tasks.add_task(send_verification_email, user.email, verification_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. A new verification email has been sent.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token type": "bearer"}

# Password reset endpoints (outline)
@router.post("/request-password-reset")
def request_password_reset(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reset_token = secrets.token_urlsafe(32)
    user.verification_token = reset_token  # Reuse the field for simplicity
    db.commit()
    # Send reset email (reuse send_verification_email for demo)
    background_tasks.add_task(send_verification_email, email, reset_token)
    return {"message": "Password reset email sent"}

@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.hashed_password = auth.get_password_hash(new_password)
    user.verification_token = None
    db.commit()
    return {"message": "Password reset successful"}

@router.get("/subscription/status")
def get_subscription_status(current_user: models.User = Depends(get_current_user)):
    """Get current user's subscription status"""
    return {
        "is_premium": current_user.is_premium,
        "subscription_status": current_user.subscription_status,
        "api_usage_count": current_user.api_usage_count,
        "api_usage_limit": current_user.api_usage_limit
    }

@router.post("/subscription/create-checkout")
def create_checkout_session(current_user: models.User = Depends(get_current_user)):
    """Create Paddle checkout session"""
    # You'll need to configure these with your actual Paddle product IDs
    paddle_vendor_id = os.getenv("PADDLE_VENDOR_ID")
    paddle_product_id = os.getenv("PADDLE_PRODUCT_ID")
    
    if not paddle_vendor_id or not paddle_product_id:
        raise HTTPException(status_code=500, detail="Paddle configuration missing")
    
    # Return checkout URL - you can customize this based on your pricing
    checkout_url = f"https://buy.paddle.com/product/{paddle_product_id}"
    
    return {
        "checkout_url": checkout_url,
        "customer_email": current_user.email,
        "user_id": current_user.id
    }

@router.get("/pricing")
def get_pricing():
    """Get available pricing plans"""
    return {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "api_calls": 10,
                "features": ["Basic sentiment analysis", "Email verification"]
            },
            {
                "name": "Premium",
                "price": 9.99,
                "api_calls": "unlimited",
                "features": ["Unlimited sentiment analysis", "Advanced tone analysis", "Priority support"]
            }
        ]
    }