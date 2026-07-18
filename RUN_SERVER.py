#!/usr/bin/env python
"""
Complete Trusted Home Platform - Simplified Standalone Version
This is a fully functional application you can run immediately
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Depends, Body, Query
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from typing import Optional, List
import uvicorn
from passlib.context import CryptContext
from jose import JWTError, jwt
from enum import Enum

# ==================== CONFIG ====================
DATABASE_URL = "sqlite:///./trusted_home.db"
SECRET_KEY = "trusted-home-secret-key-2024"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== DATABASE ====================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== MODELS ====================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    phone = Column(String)
    hashed_password = Column(String)
    city = Column(String)
    address = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="user")

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    phone = Column(String)
    hashed_password = Column(String)
    specialization = Column(String)
    city = Column(String)
    is_verified = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="worker")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    category = Column(String)
    description = Column(String)
    base_price = Column(Float)
    estimated_duration = Column(Integer)
    bookings = relationship("Booking", back_populates="service")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    booking_date = Column(DateTime)
    status = Column(String, default="pending")
    price = Column(Float)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="bookings")
    worker = relationship("Worker", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")

# ==================== SCHEMAS ====================
class UserCreate(BaseModel):
    email: str
    full_name: str
    phone: str
    city: str
    address: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    city: str
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ServiceCreate(BaseModel):
    name: str
    category: str
    description: str
    base_price: float
    estimated_duration: int

class ServiceResponse(BaseModel):
    id: int
    name: str
    category: str
    base_price: float
    class Config:
        from_attributes = True

class BookingCreate(BaseModel):
    service_id: int
    booking_date: datetime
    description: str

class BookingResponse(BaseModel):
    id: int
    service_id: int
    status: str
    price: float
    class Config:
        from_attributes = True

# ==================== AUTH ====================
def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def get_current_user(credentials: Optional[HTTPAuthCredentials] = Depends(HTTPBearer(auto_error=False)), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="No credentials")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="Trusted Home Platform",
    description="Home Services Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTES ====================
@app.get("/")
async def root():
    return {
        "message": "Welcome to Trusted Home Platform",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# AUTH
@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        city=user.city,
        address=user.address,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# USERS
@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# SERVICES
@app.get("/api/v1/services", response_model=List[ServiceResponse])
async def list_services(db: Session = Depends(get_db)):
    return db.query(Service).all()

@app.post("/api/v1/services", response_model=ServiceResponse)
async def create_service(service: ServiceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_service = Service(**service.dict())
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

# BOOKINGS
@app.get("/api/v1/bookings", response_model=List[BookingResponse])
async def list_bookings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Booking).filter(Booking.user_id == current_user.id).all()

@app.post("/api/v1/bookings", response_model=BookingResponse)
async def create_booking(booking: BookingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == booking.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    new_booking = Booking(
        user_id=current_user.id,
        service_id=booking.service_id,
        booking_date=booking.booking_date,
        description=booking.description,
        price=service.base_price
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

# ==================== INITIALIZATION ====================
def initialize_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test data if empty
    if db.query(User).count() == 0:
        # Test user
        test_user = User(
            email="user@example.com",
            full_name="Test User",
            phone="+923001234567",
            city="Karachi",
            address="123 Main Street",
            hashed_password=get_password_hash("Test@12345")
        )
        db.add(test_user)
        
        # Admin user
        admin_user = User(
            email="admin@example.com",
            full_name="Admin User",
            phone="+923001234568",
            city="Karachi",
            address="Admin Office",
            role="admin",
            hashed_password=get_password_hash("Admin@12345")
        )
        db.add(admin_user)
        
        # Test services
        services = [
            Service(name="Plumbing", category="plumber", description="Plumbing services", base_price=1500, estimated_duration=60),
            Service(name="Electricity", category="electrician", description="Electrical services", base_price=1200, estimated_duration=45),
            Service(name="AC Repair", category="ac_repair", description="AC repair", base_price=2000, estimated_duration=90),
        ]
        db.add_all(services)
        
        db.commit()
        print("✓ Database initialized with test data")
        print("✓ Test User: user@example.com / Test@12345")
        print("✓ Admin: admin@example.com / Admin@12345")
    
    db.close()

if __name__ == "__main__":
    print("Initializing database...")
    initialize_db()
    print("✓ Starting server on http://localhost:8000")
    print("✓ API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
