# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import bcrypt
import sqlite3
import feedparser
import schedule
import threading
import time
import re
from contextlib import contextmanager

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

OBITUARY_FEEDS = [
    "https://www.legacy.com/obituaries/rss/",
    "https://obittree.com/obituaries/feed/",
]

DB_NAME = "memorial_watch.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        location TEXT,
        dob TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS obituaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        location TEXT,
        date TEXT,
        source TEXT,
        link TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        watchlist_id INTEGER NOT NULL,
        obituary_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        sent BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (watchlist_id) REFERENCES watchlist (id),
        FOREIGN KEY (obituary_id) REFERENCES obituaries (id)
    )''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class WatchlistItem(BaseModel):
    name: str
    location: Optional[str] = None
    dob: Optional[str] = None

class WatchlistResponse(BaseModel):
    id: int
    name: str
    location: Optional[str]
    dob: Optional[str]
    status: str
    created_at: str

class ObituarySearch(BaseModel):
    name: str
    location: Optional[str] = None

class ObituaryResult(BaseModel):
    id: int
    name: str
    age: Optional[int]
    location: Optional[str]
    date: Optional[str]
    source: str
    link: Optional[str]
    confidence: str

app = FastAPI(title="Memorial Watch API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    with get_db() as conn:
        c = conn.cursor()
        
        c.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        password_hash = hash_password(user.password)
        c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                  (user.email, password_hash))
        conn.commit()
        
        user_id = c.lastrowid
        access_token = create_access_token(data={"sub": user_id})
        
        return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    with get_db() as conn:
        c = conn.cursor()
       c.execute("SELECT id, password_hash FROM users WHERE email = ?", (user.email,))
        result = c.fetchone()
        
        if not result or not verify_password(user.password, result['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": result['id']})
