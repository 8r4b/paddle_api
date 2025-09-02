from fastapi import FastAPI, Request, HTTPException, Depends
from app import models, database
from app.users import router as users_router
from app.sentiment import router as sentiment_router
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import hmac
import hashlib
from datetime import datetime
from app.database import engine

# Create all tables
models.Base.metadata.create_all(bind=engine)

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
@app.post("/webhooks/paddle")
async def paddle_webhook(request: Request, db: Session = Depends(database.get_db)):
    try:
        data = await request.json()
        
        # For Paddle's new API, authentication is done via API key
        # No signature verification needed as in the classic API
        
        # Log the webhook data for debugging
        print(f"Received Paddle webhook: {data}")
        
        alert_name = data.get("alert_name")
        
        if alert_name == "subscription_created":
            # Handle new subscription
            user_email = data.get("email")
            subscription_id = data.get("subscription_id")
            plan_id = data.get("plan_id")
            
            user = db.query(models.User).filter(models.User.email == user_email).first()
            if user:
                user.is_subscribed = True
                user.subscription_id = subscription_id
                user.subscription_plan_id = plan_id
                user.subscription_status = "active"
                user.subscription_start_date = datetime.now()
                db.commit()
                print(f"User {user.username} subscription activated")
            
        elif alert_name == "subscription_cancelled":
            subscription_id = data.get("subscription_id")
            
            user = db.query(models.User).filter(models.User.subscription_id == subscription_id).first()
            if user:
                user.subscription_status = "cancelled"
                user.subscription_end_date = datetime.now()
                db.commit()
                print(f"User {user.username} subscription cancelled")
                
        elif alert_name == "subscription_payment_succeeded":
            # Handle successful payment
            subscription_id = data.get("subscription_id")
            
            user = db.query(models.User).filter(models.User.subscription_id == subscription_id).first()
            if user:
                # Extend subscription end date if needed
                # This depends on your subscription model
                print(f"Payment succeeded for user {user.username}")
                
        # Return 200 OK to acknowledge receipt
        return {"status": "success"}
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        # Still return 200 to prevent Paddle from retrying
        return {"status": "error", "message": str(e)}
