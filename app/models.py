from sqlalchemy import Column, Integer, String,Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

# SQLAlchemy User model
class User(Base):
	__tablename__ = "users"
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(50), unique=True, index=True, nullable=False)
	email = Column(String(100), unique=True, index=True, nullable=False)
	hashed_password = Column(String(255), nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow)
	is_verified = Column(Boolean, default=False)
	verification_code = Column(String(255), nullable=True)
	verification_token = Column(String(255), nullable=True)
	# Paddle subscription fields
	subscription_id = Column(String, nullable=True)
	subscription_status = Column(String, default="inactive")
	is_premium = Column(Boolean, default=False)
	api_usage_count = Column(Integer, default=0)
	api_usage_limit = Column(Integer, default=10)  # Free tier limit
	# Relationship to analysis results
	analyses = relationship("EmailAnalysis", back_populates="user")

# SQLAlchemy EmailAnalysis model
class EmailAnalysis(Base):
	__tablename__ = "email_analyses"
	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	email_text = Column(Text, nullable=False)
	sentiment = Column(String(50))
	tone = Column(String(50))
	analyzed_at = Column(DateTime, default=datetime.utcnow)
	user = relationship("User", back_populates="analyses")

# Pydantic schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr  # This will validate email format
    password: str

class UserRead(BaseModel):
	id: int
	username: str
	email: str
	created_at: datetime
	class Config:
		orm_mode = True

class EmailAnalysisCreate(BaseModel):
	email_text: str

class EmailAnalysisRead(BaseModel):
	id: int
	email_text: str
	sentiment: Optional[str]
	tone: Optional[str]
	analyzed_at: datetime
	class Config:
		from_attributes = True