from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_current_user
from app import models, database
import openai
import os

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Load OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

@router.post("/analyze")
def analyze_email(
    analysis: models.EmailAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Call OpenAI API for sentiment and tone analysis
    try:
        prompt = f"Analyze the following email for sentiment and tone. Return both as short labels.\n\nEmail:\n{analysis.email_text}"
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        result = response.choices[0].message.content.strip()
        # Example: "Sentiment: Positive\nTone: Friendly"
        sentiment = None
        tone = None
        for line in result.splitlines():
            if "sentiment" in line.lower():
                sentiment = line.split(":")[-1].strip()
            if "tone" in line.lower():
                tone = line.split(":")[-1].strip()
        # Store in DB
        db_analysis = models.EmailAnalysis(
            user_id=current_user.id if hasattr(current_user, 'id') else None,
            email_text=analysis.email_text,
            sentiment=sentiment,
            tone=tone
        )
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        return {
            "sentiment": sentiment,
            "tone": tone,
            "analyzed_at": db_analysis.analyzed_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))