from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import models, auth, database
from app.models import UserCreate, UserRead
from fastapi.security import OAuth2PasswordRequestForm
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_verification_email(email: str, token: str, subject: str, body: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = smtp_user
    to_email = email

    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        print("SMTP environment variables not set. Email not sent.")
        return

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
        print(f"Failed to send email: {e}")

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    db_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

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

    # Schedule email verification
    subject = "Verify your email"
    verify_link = f"https://your-domain.com/users/verify?token={verification_token}" # Replace with your actual domain
    body = f"Thank you for registering! Please verify your email by clicking the following link: {verify_link}"
    background_tasks.add_task(send_verification_email, user.email, verification_token, subject, body)

    return new_user

@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user or user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")
    
    user.is_verified = True
    user.verification_token = None # Clear the token after verification
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email to log in.")
        
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Password reset endpoints
@router.post("/request-password-reset")
def request_password_reset(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User with this email not found")
        
    # Generate a unique token for password reset
    reset_token = secrets.token_urlsafe(32)
    user.verification_token = reset_token # Reusing verification_token field for simplicity, consider a dedicated field
    db.commit()
    
    # Send reset email
    subject = "Password Reset Request"
    reset_link = f"https://your-domain.com/users/reset-password?token={reset_token}" # Replace with your actual domain
    body = f"You requested a password reset. Please click the following link to reset your password: {reset_link}"
    background_tasks.add_task(send_verification_email, email, reset_token, subject, body)
    
    return {"message": "Password reset instructions sent to your email."}

@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    
    if not user or user.is_verified == False: # Check if token is valid and user exists
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired password reset token")
        
    user.hashed_password = auth.get_password_hash(new_password)
    user.verification_token = None # Clear the token after reset
    db.commit()
    
    return {"message": "Password reset successfully"}

# Placeholder for sentiment analysis endpoint (assuming it exists in app.main or elsewhere)
# If sentiment analysis is part of this file and not in app.main, it should be moved here or imported.
# Example placeholder:
# from app.sentiment_analyzer import analyze_sentiment
# 
# @router.post("/analyze")
# def analyze_text_sentiment(text: str, token: str = Depends(auth.oauth2_scheme)):
#     # Ensure user is authenticated and authorized if needed
#     # You would typically decode the token here to get user info
#     try:
#         payload = auth.verify_access_token(token)
#         username = payload.get("sub")
#         if not username:
#              raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
#     except:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
#     
#     sentiment = analyze_sentiment(text) # Assuming analyze_sentiment function exists
#     return {"text": text, "sentiment": sentiment}