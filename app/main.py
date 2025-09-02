from fastapi import FastAPI, Request, HTTPException, Depends
from app import models, database
from app.users import router as users_router
from app.sentiment import router as sentiment_router
from app.dependencies import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import hashlib
import hmac
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Email Sentiment & Tone Analyzer API",
    description="Analyze email sentiment and tone with authentication.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Email Sentiment & Tone Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "register": "/users/register",
            "login": "/users/token",
            "verify": "/users/verify",
            "analyze": "/sentiment/analyze"
        }
    }
# Include routers
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(sentiment_router, prefix="/sentiment", tags=["sentiment"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Paddle Webhook Endpoint
@app.post("/paddle/webhook")
async def paddle_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        # Get the raw body and headers
        body = await request.body()
        signature = request.headers.get("paddle-signature")

        if not signature:
            raise HTTPException(status_code=400, detail="Missing Paddle signature")

        # Verify the webhook signature
        webhook_secret = os.getenv("PADDLE_WEBHOOK_SECRET")
        if not verify_paddle_signature(body, signature, webhook_secret):
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Parse the webhook data
        import json
        webhook_data = json.loads(body.decode('utf-8'))
        event_type = webhook_data.get("event_type")

        # Handle different webhook events
        if event_type == "subscription_created":
            await handle_subscription_created(webhook_data, db)
        elif event_type == "subscription_updated":
            await handle_subscription_updated(webhook_data, db)
        elif event_type == "subscription_cancelled":
            await handle_subscription_cancelled(webhook_data, db)
        elif event_type == "transaction_completed":
            await handle_transaction_completed(webhook_data, db)

        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

def verify_paddle_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Paddle webhook signature"""
    try:
        # Extract timestamp and signature from header
        parts = signature.split(";")
        timestamp = None
        signature_hash = None

        for part in parts:
            if part.startswith("ts="):
                timestamp = part[3:]
            elif part.startswith("h1="):
                signature_hash = part[3:]

        if not timestamp or not signature_hash:
            return False

        # Create the signature payload
        payload = f"{timestamp};{body.decode('utf-8')}"

        # Compute HMAC
        computed_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature_hash, computed_signature)
    except Exception:
        return False

async def handle_subscription_created(data: dict, db: Session):
    """Handle new subscription creation"""
    customer_email = data.get("data", {}).get("custom_data", {}).get("user_email")
    subscription_id = data.get("data", {}).get("id")

    if customer_email:
        user = db.query(models.User).filter(models.User.email == customer_email).first()
        if user:
            user.subscription_id = subscription_id
            user.subscription_status = "active"
            user.is_premium = True
            db.commit()

async def handle_subscription_updated(data: dict, db: Session):
    """Handle subscription updates"""
    subscription_id = data.get("data", {}).get("id")
    status = data.get("data", {}).get("status")

    user = db.query(models.User).filter(models.User.subscription_id == subscription_id).first()
    if user:
        user.subscription_status = status
        user.is_premium = status == "active"
        db.commit()

async def handle_subscription_cancelled(data: dict, db: Session):
    """Handle subscription cancellation"""
    subscription_id = data.get("data", {}).get("id")

    user = db.query(models.User).filter(models.User.subscription_id == subscription_id).first()
    if user:
        user.subscription_status = "cancelled"
        user.is_premium = False
        db.commit()

async def handle_transaction_completed(data: dict, db: Session):
    """Handle completed transactions"""
    # You can add logic here to track successful payments
    customer_email = data.get("data", {}).get("custom_data", {}).get("user_email")
    amount = data.get("data", {}).get("details", {}).get("totals", {}).get("total")

    if customer_email:
        user = db.query(models.User).filter(models.User.email == customer_email).first()
        if user:
            # Log the transaction or update credits/usage
            print(f"Payment completed for {customer_email}: ${amount}")

# Paddle subscription management endpoints
@app.post("/paddle/create-checkout")
async def create_paddle_checkout(
    current_user: models.User = Depends(get_current_user)
):
    """Create a Paddle checkout session"""
    try:
        # This would integrate with Paddle's API to create a checkout
        # You'll need to implement this based on Paddle's SDK
        checkout_url = f"https://checkout.paddle.com/subscription?{current_user.email}"
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to create checkout")