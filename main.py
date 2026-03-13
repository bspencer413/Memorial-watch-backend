# main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
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

# ============================================================================

# CONFIGURATION

# ============================================================================

SECRET_KEY = “your-secret-key-change-in-production”
ALGORITHM = “HS256”
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# Obituary RSS feeds to monitor

OBITUARY_FEEDS = [
“https://www.legacy.com/obituaries/rss/”,
“https://obittree.com/obituaries/feed/”,
]

# ============================================================================

# DATABASE SETUP

# ============================================================================

DB_NAME = “memorial_watch.db”

def init_db():
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

```
# Users table
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# Watchlist table
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

# Obituaries table (scraped data)
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

# Notifications table
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
```

@contextmanager
def get_db():
conn = sqlite3.connect(DB_NAME)
conn.row_factory = sqlite3.Row
try:
yield conn
finally:
conn.close()

# ============================================================================

# PYDANTIC MODELS

# ============================================================================

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

# ============================================================================

# FASTAPI APP

# ============================================================================

app = FastAPI(title=“Memorial Watch API”, version=“1.0.0”)

# CORS middleware

app.add_middleware(
CORSMiddleware,
allow_origins=[”*”],  # In production, specify your frontend domain
allow_credentials=True,
allow_methods=[”*”],
allow_headers=[”*”],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=“auth/login”)

# ============================================================================

# AUTH UTILITIES

# ============================================================================

def hash_password(password: str) -> str:
return bcrypt.hashpw(password.encode(‘utf-8’), bcrypt.gensalt()).decode(‘utf-8’)

def verify_password(plain_password: str, hashed_password: str) -> bool:
return bcrypt.checkpw(plain_password.encode(‘utf-8’), hashed_password.encode(‘utf-8’))

def create_access_token(data: dict):
to_encode = data.copy()
expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
to_encode.update({“exp”: expire})
encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
try:
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
user_id: int = payload.get(“sub”)
if user_id is None:
raise HTTPException(status_code=401, detail=“Invalid authentication”)
return user_id
except jwt.ExpiredSignatureError:
raise HTTPException(status_code=401, detail=“Token expired”)
except jwt.JWTError:
raise HTTPException(status_code=401, detail=“Invalid token”)

# ============================================================================

# AUTH ENDPOINTS

# ============================================================================

@app.post(”/auth/register”, response_model=Token)
async def register(user: UserCreate):
with get_db() as conn:
c = conn.cursor()

```
    # Check if user exists
    c.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if c.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    password_hash = hash_password(user.password)
    c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
              (user.email, password_hash))
    conn.commit()
    
    user_id = c.lastrowid
    access_token = create_access_token(data={"sub": user_id})
    
    return {"access_token": access_token, "token_type": "bearer"}
```

@app.post(”/auth/login”, response_model=Token)
async def login(user: UserLogin):
with get_db() as conn:
c = conn.cursor()
c.execute(“SELECT id, password_hash FROM users WHERE email = ?”, (user.email,))
result = c.fetchone()

```
    if not result or not verify_password(user.password, result['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": result['id']})
    return {"access_token": access_token, "token_type": "bearer"}
```

# ============================================================================

# WATCHLIST ENDPOINTS

# ============================================================================

@app.get(”/watchlist”, response_model=List[WatchlistResponse])
async def get_watchlist(user_id: int = Depends(get_current_user)):
with get_db() as conn:
c = conn.cursor()
c.execute(”””
SELECT id, name, location, dob, status, created_at
FROM watchlist
WHERE user_id = ? AND status = ‘active’
ORDER BY created_at DESC
“””, (user_id,))

```
    items = []
    for row in c.fetchall():
        items.append({
            "id": row['id'],
            "name": row['name'],
            "location": row['location'],
            "dob": row['dob'],
            "status": row['status'],
            "created_at": row['created_at']
        })
    
    return items
```

@app.post(”/watchlist”)
async def add_to_watchlist(item: WatchlistItem, user_id: int = Depends(get_current_user)):
with get_db() as conn:
c = conn.cursor()
c.execute(”””
INSERT INTO watchlist (user_id, name, location, dob)
VALUES (?, ?, ?, ?)
“””, (user_id, item.name, item.location, item.dob))
conn.commit()

```
    return {"message": "Added to watchlist", "id": c.lastrowid}
```

@app.delete(”/watchlist/{item_id}”)
async def remove_from_watchlist(item_id: int, user_id: int = Depends(get_current_user)):
with get_db() as conn:
c = conn.cursor()
c.execute(“UPDATE watchlist SET status = ‘deleted’ WHERE id = ? AND user_id = ?”,
(item_id, user_id))
conn.commit()

```
    if c.rowcount == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"message": "Removed from watchlist"}
```

# ============================================================================

# SEARCH ENDPOINT

# ============================================================================

@app.post(”/search”, response_model=List[ObituaryResult])
async def search_obituaries(search: ObituarySearch):
with get_db() as conn:
c = conn.cursor()

```
    # Build search query
    query = "SELECT * FROM obituaries WHERE name LIKE ?"
    params = [f"%{search.name}%"]
    
    if search.location:
        query += " AND location LIKE ?"
        params.append(f"%{search.location}%")
    
    query += " ORDER BY scraped_at DESC LIMIT 20"
    
    c.execute(query, params)
    
    results = []
    for row in c.fetchall():
        # Calculate confidence based on name match
        confidence = calculate_confidence(search.name, row['name'], search.location, row['location'])
        
        results.append({
            "id": row['id'],
            "name": row['name'],
            "age": row['age'],
            "location": row['location'],
            "date": row['date'],
            "source": row['source'],
            "link": row['link'],
            "confidence": confidence
        })
    
    return results
```

def calculate_confidence(search_name: str, found_name: str,
search_loc: Optional[str], found_loc: Optional[str]) -> str:
“”“Calculate match confidence”””
search_name = search_name.lower()
found_name = found_name.lower()

```
# Exact match
if search_name == found_name:
    if search_loc and found_loc and search_loc.lower() in found_loc.lower():
        return "high"
    return "medium"

# Partial match
if search_name in found_name or found_name in search_name:
    return "medium"

return "low"
```

# ============================================================================

# OBITUARY SCRAPER

# ============================================================================

def scrape_obituaries():
“”“Scrape RSS feeds for new obituaries”””
print(f”[{datetime.now()}] Starting obituary scrape…”)

```
with get_db() as conn:
    c = conn.cursor()
    
    for feed_url in OBITUARY_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:50]:  # Limit to 50 most recent
                title = entry.get('title', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                
                # Extract name from title
                name = extract_name_from_title(title)
                if not name:
                    continue
                
                # Check if already in DB
                c.execute("SELECT id FROM obituaries WHERE link = ?", (link,))
                if c.fetchone():
                    continue
                
                # Extract age and location if possible
                age = extract_age(title)
                location = extract_location(title)
                
                # Insert into database
                c.execute("""
                    INSERT INTO obituaries (name, age, location, date, source, link)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, age, location, published, feed_url, link))
            
            conn.commit()
            print(f"Processed {feed_url}")
            
        except Exception as e:
            print(f"Error scraping {feed_url}: {e}")
    
    # Check for matches with watchlist
    check_watchlist_matches()
```

def extract_name_from_title(title: str) -> Optional[str]:
“”“Extract person’s name from obituary title”””
# Common patterns: “John Doe, 78”, “John Doe Obituary”, etc.
# Remove common words
title = re.sub(r’\b(obituary|dies|passed|age|aged)\b’, ‘’, title, flags=re.IGNORECASE)
# Remove numbers (ages)
title = re.sub(r’\d+’, ‘’, title)
# Clean up
title = re.sub(r’[,-|]’, ’ ’, title).strip()

```
if len(title) > 3 and len(title) < 100:
    return title
return None
```

def extract_age(text: str) -> Optional[int]:
“”“Extract age from text”””
match = re.search(r’\b(\d{1,3})\b’, text)
if match:
age = int(match.group(1))
if 0 < age < 120:
return age
return None

def extract_location(text: str) -> Optional[str]:
“”“Extract location from text”””
# Look for city, state patterns
match = re.search(r’([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s+[A-Z]{2})’, text)
if match:
return match.group(1)
return None

def check_watchlist_matches():
“”“Check scraped obituaries against watchlist”””
with get_db() as conn:
c = conn.cursor()

```
    # Get all active watchlist items
    c.execute("SELECT * FROM watchlist WHERE status = 'active'")
    watchlist_items = c.fetchall()
    
    for watch in watchlist_items:
        # Search for matching obituaries
        query = "SELECT * FROM obituaries WHERE name LIKE ?"
        params = [f"%{watch['name']}%"]
        
        if watch['location']:
            query += " AND location LIKE ?"
            params.append(f"%{watch['location']}%")
        
        c.execute(query, params)
        matches = c.fetchall()
        
        for obit in matches:
            # Check if notification already sent
            c.execute("""
                SELECT id FROM notifications 
                WHERE watchlist_id = ? AND obituary_id = ?
            """, (watch['id'], obit['id']))
            
            if not c.fetchone():
                # Create notification
                message = f"Possible match found: {obit['name']} in {obit['location'] or 'unknown location'}"
                c.execute("""
                    INSERT INTO notifications (user_id, watchlist_id, obituary_id, message)
                    VALUES (?, ?, ?, ?)
                """, (watch['user_id'], watch['id'], obit['id'], message))
                
                print(f"Created notification for user {watch['user_id']}: {message}")
    
    conn.commit()
```

# ============================================================================

# NOTIFICATIONS ENDPOINT

# ============================================================================

@app.get(”/notifications”)
async def get_notifications(user_id: int = Depends(get_current_user)):
with get_db() as conn:
c = conn.cursor()
c.execute(”””
SELECT n.id, n.message, n.created_at, w.name, o.link
FROM notifications n
JOIN watchlist w ON n.watchlist_id = w.id
JOIN obituaries o ON n.obituary_id = o.id
WHERE n.user_id = ?
ORDER BY n.created_at DESC
LIMIT 50
“””, (user_id,))

```
    notifications = []
    for row in c.fetchall():
        notifications.append({
            "id": row['id'],
            "name": row['name'],
            "message": row['message'],
            "created_at": row['created_at'],
            "link": row['link']
        })
    
    return notifications
```

# ============================================================================

# BACKGROUND SCHEDULER

# ============================================================================

def run_scheduler():
“”“Run background tasks”””
schedule.every(1).hours.do(scrape_obituaries)

```
while True:
    schedule.run_pending()
    time.sleep(60)
```

# ============================================================================

# HEALTH CHECK

# ============================================================================

@app.get(”/health”)
async def health_check():
return {
“status”: “healthy”,
“timestamp”: datetime.now().isoformat(),
“version”: “1.0.0”
}

# ============================================================================

# STARTUP

# ============================================================================

@app.on_event(“startup”)
async def startup_event():
init_db()
print(“Database initialized”)

```
# Start background scheduler in separate thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()
print("Background scheduler started")

# Run initial scrape
threading.Thread(target=scrape_obituaries, daemon=True).start()
```

if **name** == “**main**”:
import uvicorn
uvicorn.run(app, host=“0.0.0.0”, port=8000)
