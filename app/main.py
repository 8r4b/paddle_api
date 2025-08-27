from fastapi import FastAPI
from app import models, database
from app.users import router as users_router
from app.sentiment import router as sentiment_router
from fastapi.middleware.cors import CORSMiddleware

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