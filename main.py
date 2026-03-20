# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import bcrypt
import psycopg2
import psycopg2.extras
import os
import feedparser
import schedule
import threading
import time
import re
from contextlib import contextmanager

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080
# Legacy.com newspaper RSS feeds — recentdate=3 pulls 1 year of obituaries
OBITUARY_FEEDS = [
    # Northeast
    "https://www.legacy.com/obituaries/nhregister/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/bostonglobe/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/nytimes/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/philly/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/washingtonpost/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/baltimoresun/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/courant/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/pressherald/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/newsday/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/buffalonews/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/syracuse/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/timesunion/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/providencejournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/delawareonline/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/app/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/northjersey/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/nj/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/poconorecord/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/citizensvoice/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/timesleader/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/pittsburghpostgazette/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/fredericksburg/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/roanoke/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/richmond/services/rss.ashx?recentdate=3",
    # Southeast
    "https://www.legacy.com/obituaries/orlandosentinel/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/miamiherald/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/charlotteobserver/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/ajc/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/tennessean/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/nola/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/sunherald/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/clarionledger/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/tallahassee/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/jacksonville/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/tampabay/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/heraldonline/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/thestate/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/islandpacket/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/newsobserver/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/greensboro/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/kentucky/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/courier-journal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/huntsville/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/al/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/arkansasonline/services/rss.ashx?recentdate=3",
    # Midwest
    "https://www.legacy.com/obituaries/chicagotribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/freep/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/startribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/indystar/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/stltoday/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/kansascity/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/cleveland/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/omaha/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/dispatch/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/cincinnati/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/dayton/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/akron/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/toledo/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/journalsentinel/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/madison/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/greenbaypressgazette/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/postcrescent/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/lansingstatejournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/grandrapids/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/southbendtribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/jconline/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/fortwayne/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/evansville/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/siouxcityjournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/desmoinesregister/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/duluthnewstribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/rapidcityjournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/argusleader/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/bismarcktribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/grandforksherald/services/rss.ashx?recentdate=3",
    # Southwest
    "https://www.legacy.com/obituaries/azcentral/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/dallasnews/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/houstonchronicle/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/expressnews/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/abqjournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/tulsaworld/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/oklahoman/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/lubbockonline/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/caller/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/elpasotimes/services/rss.ashx?recentdate=3",
    # West
    "https://www.legacy.com/obituaries/latimes/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/sfgate/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/oregonlive/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/seattletimes/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/denverpost/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/sltrib/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/sacbee/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/fresnobee/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/modbee/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/mercedsunstar/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/thenewstribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/spokesman/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/idahostatesman/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/montanastandard/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/greatfallstribune/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/billingsgazette/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/nevadaappeal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/rgj/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/reviewjournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/coloradoan/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/gjsentinel/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/wyomingfacts/services/rss.ashx?recentdate=3",
    # Hawaii & Alaska
    "https://www.legacy.com/obituaries/staradvertiser/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/adn/services/rss.ashx?recentdate=3",
]
DB_HOST = "dpg-d6qhp3ngi27c73a3ivag-a.oregon-postgres.render.com"
DB_USER = "memorial_watch_db_user"
DB_PASS = "9IkXRdY8NcZSKy0yw5b7viPdtIrVIITR"
DB_NAME = "memorial_watch_db"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        location TEXT,
        dob TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS obituaries (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        name_normalized TEXT,
        age INTEGER,
        location TEXT,
        date TEXT,
        source TEXT,
        link TEXT,
        obit_text TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        watchlist_id INTEGER NOT NULL,
        obituary_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        sent BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (watchlist_id) REFERENCES watchlist (id),
        FOREIGN KEY (obituary_id) REFERENCES obituaries (id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS death_records (
        id SERIAL PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        birth_date TEXT,
        death_date TEXT,
        state TEXT,
        zip_code TEXT,
        source TEXT DEFAULT 'SSDI',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_obituaries_name
        ON obituaries (name)''')
    c.execute('''ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS name_normalized TEXT''')
    c.execute('''ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS obit_text TEXT''')
    c.execute('''ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS link TEXT''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_obituaries_name_normalized
    ON obituaries (name_normalized)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_obituaries_name_normalized
        ON obituaries (name_normalized)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_death_records_last_name
        ON death_records (last_name)''')

    conn.commit()
    conn.close()


@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()


def normalize_name(name: str) -> str:
    """Convert 'Last, First' to 'First Last' and title case"""
    if not name:
        return name
    name = name.strip()
    if ',' in name:
        parts = name.split(',', 1)
        name = f"{parts[1].strip()} {parts[0].strip()}"
    # Fix apostrophe capitalization (O'Connor, etc.)
    name = re.sub(r"\b\w+'\w+\b", lambda m: m.group(0).title(), name)
    return name.title()


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
    birth_year: Optional[str] = None

class ObituaryResult(BaseModel):
    id: int
    name: str
    age: Optional[int]
    location: Optional[str]
    date: Optional[str]
    source: str
    link: Optional[str]
    obit_text: Optional[str]
    confidence: str


app = FastAPI(title="Memory Watch API", version="1.2.0")

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


# ── HEALTH & DIAGNOSTICS ──────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0"
    }

@app.get("/admin/stats")
async def get_stats():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM obituaries")
        obit_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM death_records")
        death_count = c.fetchone()[0]
        c.execute("""SELECT name, date, source FROM obituaries
            ORDER BY scraped_at DESC LIMIT 5""")
        recent = c.fetchall()
        return {
            "obituaries": obit_count,
            "death_records": death_count,
            "most_recent": [{"name": r[0], "date": r[1],
                "source": r[2]} for r in recent]
        }

@app.get("/admin/scrape-now")
async def scrape_now():
    threading.Thread(target=scrape_obituaries, daemon=True).start()
    return {"message": "Scrape started — check /admin/stats in 60 seconds"}


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        password_hash = hash_password(user.password)
        c.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            (user.email, password_hash))
        user_id = c.fetchone()[0]
        conn.commit()
        access_token = create_access_token(data={"sub": user_id})
        return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM users WHERE email = %s",
            (user.email,))
        result = c.fetchone()
        if not result or not verify_password(user.password, result[1]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = create_access_token(data={"sub": result[0]})
        return {"access_token": access_token, "token_type": "bearer"}


# ── ACCOUNT ───────────────────────────────────────────────────────────────────

@app.delete("/account")
async def delete_account(user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM watchlist WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return {"message": "Account permanently deleted"}


# ── WATCHLIST ─────────────────────────────────────────────────────────────────

@app.get("/watchlist", response_model=List[WatchlistResponse])
async def get_watchlist(user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, location, dob, status, created_at
            FROM watchlist
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))
        items = []
        for row in c.fetchall():
            items.append({
                "id": row[0], "name": row[1], "location": row[2],
                "dob": row[3], "status": row[4], "created_at": str(row[5])
            })
        return items

@app.post("/watchlist")
async def add_to_watchlist(item: WatchlistItem,
        user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO watchlist (user_id, name, location, dob)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (user_id, item.name, item.location, item.dob))
        conn.commit()
        item_id = c.fetchone()[0]
        return {"message": "Added to watchlist", "id": item_id}

@app.delete("/watchlist/{item_id}")
async def remove_from_watchlist(item_id: int,
        user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE watchlist SET status = 'deleted' WHERE id = %s AND user_id = %s",
            (item_id, user_id))
        conn.commit()
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Removed from watchlist"}


# ── SEARCH ────────────────────────────────────────────────────────────────────

@app.post("/search", response_model=List[ObituaryResult])
async def search_obituaries(search: ObituarySearch):
    with get_db() as conn:
        c = conn.cursor()
        results = []
        search_normalized = normalize_name(search.name)

        # Search both original and normalized name in database
        query = """SELECT * FROM obituaries WHERE
            name ILIKE %s OR name_normalized ILIKE %s"""
        params = [f"%{search.name}%", f"%{search_normalized}%"]

        if search.location:
            query += " AND location ILIKE %s"
            params.append(f"%{search.location}%")
        if search.birth_year:
            query += " AND date LIKE %s"
            params.append(f"%{search.birth_year}%")
        query += " ORDER BY scraped_at DESC LIMIT 20"
        c.execute(query, params)

        for row in c.fetchall():
            confidence = calculate_confidence(
                search.name, row[1], search.location, row[3])
            results.append({
                "id": row[0],
                "name": row[1],
                "age": row[2],
                "location": row[3],
                "date": row[4],
                "source": "Legacy",
                "link": row[6],
                "obit_text": row[7] if len(row) > 7 else None,
                "confidence": confidence
            })

               # Live search disabled pending optimization
        return results


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@app.get("/notifications")
async def get_notifications(user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT n.id, n.message, n.created_at, w.name, o.link
            FROM notifications n
            JOIN watchlist w ON n.watchlist_id = w.id
            JOIN obituaries o ON n.obituary_id = o.id
            WHERE n.user_id = %s
            ORDER BY n.created_at DESC LIMIT 50
        """, (user_id,))
        notifications = []
        for row in c.fetchall():
            notifications.append({
                "id": row[0], "name": row[3],
                "message": row[1], "created_at": str(row[2]),
                "link": row[4]
            })
        return notifications

async def search_legacy_live(name: str, location: str = None):
    """Search Legacy RSS feeds in real time when database has no results"""
    import aiohttp
    
    results = []
    name_parts = name.strip().lower().split()
    if len(name_parts) < 2:
        return results

    # Search a subset of high-volume feeds with longer date range
    live_feeds = [
    "https://www.legacy.com/obituaries/desmoinesregister/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/chicagotribune/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/startribune/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/stltoday/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/omaha/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/wcfcourier/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/globegazette/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/siouxcityjournal/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/thegazette/services/rss.ashx?recentdate=365",
    "https://www.legacy.com/obituaries/qctimes/services/rss.ashx?recentdate=365",
]


    try:
        async with aiohttp.ClientSession() as session:
            for feed_url in live_feeds:
                try:
                    async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            feed = feedparser.parse(content)
                            for entry in feed.entries:
                                title = entry.get('title', '').strip()
                                title_lower = title.lower()
                                # Check if all name parts appear in the title
                                if all(part in title_lower for part in name_parts):
                                    link = entry.get('link', '')
                                    published = entry.get('published', '')
                                    obit_text = entry.get('summary', '') or entry.get('description', '')
                                    obit_text = re.sub(r'<[^>]+>', '', obit_text).strip()
                                    name_normalized = normalize_name(title)
                                    loc = extract_location(title)
                                    age = extract_age(title)
                                    results.append({
                                        "id": -(len(results) + 1),
                                        "name": name_normalized,
                                        "age": age,
                                        "location": loc,
                                        "date": published,
                                        "source": "Legacy (live)",
                                        "link": link,
                                        "obit_text": obit_text,
                                        "confidence": calculate_confidence(
                                            name, name_normalized, location, loc)
                                    })
                                    if len(results) >= 10:
                                        return results
                except Exception as e:
                    print(f"Live feed error {feed_url}: {e}")
                    continue
    except Exception as e:
        print(f"Live search session error: {e}")

    return results

# ── SCRAPER ───────────────────────────────────────────────────────────────────

def scrape_obituaries():
    print(f"[{datetime.now()}] Starting obituary scrape...")
    total = 0
    with get_db() as conn:
        c = conn.cursor()
        for feed_url in OBITUARY_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                count = 0
                for entry in feed.entries:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    # Get full obituary text from RSS description
                    obit_text = entry.get('summary', '') or entry.get('description', '')
                    # Strip HTML tags from obit text
                    obit_text = re.sub(r'<[^>]+>', '', obit_text).strip()

                    if not title or len(title) < 3:
                        continue

                    # Check for duplicate by link
                    if link:
                        c.execute("SELECT id FROM obituaries WHERE link = %s",
                            (link,))
                        if c.fetchone():
                            continue

                    # Normalize name — convert "Last, First" to "First Last"
                    name_normalized = normalize_name(title)
                    age = extract_age(title)
                    location = extract_location(title)

                    c.execute("""
                        INSERT INTO obituaries
                        (name, name_normalized, age, location, date,
                         source, link, obit_text)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (title, name_normalized, age, location,
                          published, feed_url, link, obit_text))
                    count += 1

                conn.commit()
                total += count
                print(f"  {feed_url}: {count} new entries")

            except Exception as e:
                print(f"  ERROR {feed_url}: {e}")

    print(f"[{datetime.now()}] Scrape complete. {total} new obituaries added.")
    check_watchlist_matches()


def extract_age(text: str) -> Optional[int]:
    match = re.search(r'\b(\d{1,3})\b', text)
    if match:
        age = int(match.group(1))
        if 0 < age < 120:
            return age
    return None

def extract_location(text: str) -> Optional[str]:
    match = re.search(
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s+[A-Z]{2})', text)
    if match:
        return match.group(1)
    return None

def check_watchlist_matches():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM watchlist WHERE status = 'active'")
        watchlist_items = c.fetchall()
        for watch in watchlist_items:
            watch_name = watch[2]
            watch_normalized = normalize_name(watch_name)
            c.execute("""SELECT * FROM obituaries WHERE
                name ILIKE %s OR name_normalized ILIKE %s""",
                (f"%{watch_name}%", f"%{watch_normalized}%"))
            matches = c.fetchall()
            for obit in matches:
                c.execute("""
                    SELECT id FROM notifications
                    WHERE watchlist_id = %s AND obituary_id = %s
                """, (watch[0], obit[0]))
                if not c.fetchone():
                    message = f"Possible match found: {obit[1]} in {obit[3] or 'unknown location'}"
                    c.execute("""
                        INSERT INTO notifications
                        (user_id, watchlist_id, obituary_id, message)
                        VALUES (%s, %s, %s, %s)
                    """, (watch[1], watch[0], obit[0], message))
                    print(f"Notification created for user {watch[1]}: {message}")
        conn.commit()


def run_scheduler():
    schedule.every(1).hours.do(scrape_obituaries)
    while True:
        schedule.run_pending()
        time.sleep(60)


# ── STARTUP ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Background scheduler started")
    threading.Thread(target=scrape_obituaries, daemon=True).start()
    print("Initial scrape started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
