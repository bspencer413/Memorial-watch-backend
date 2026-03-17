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

OBITUARY_FEEDS = [
    
    # National
    "https://www.legacy.com/rss/recent-obituaries/",
    "https://www.tributes.com/rss/obituaries",
    
    # Northeast
    "https://obits.nj.com/rss/obituaries",
    "https://obits.masslive.com/rss/obituaries",
    "https://obits.pennlive.com/rss/obituaries",
    "https://obits.lehighvalleylive.com/rss/obituaries",
    "https://obits.silive.com/rss/obituaries",
    "https://obits.newyorkupstate.com/rss/obituaries",
    "https://obits.syracuse.com/rss/obituaries",
    "https://obits.cleveland.com/rss/obituaries",
    "https://obits.mlive.com/rss/obituaries",
    
    # Southeast
    "https://obits.al.com/rss/obituaries",
    "https://obits.nola.com/rss/obituaries",
    "https://obits.tennessean.com/rss/obituaries",
    "https://obits.charlotteobserver.com/rss/obituaries",
    "https://obits.thestate.com/rss/obituaries",
    "https://obits.miamiherald.com/rss/obituaries",
    "https://obits.orlandosentinel.com/rss/obituaries",
    
    # Midwest
    "https://obits.chicagotribune.com/rss/obituaries",
    "https://obits.freep.com/rss/obituaries",
    "https://obits.startribune.com/rss/obituaries",
    "https://obits.indystar.com/rss/obituaries",
    "https://obits.omaha.com/rss/obituaries",
    "https://obits.stltoday.com/rss/obituaries",
    "https://obits.kansascity.com/rss/obituaries",
    
    # Southwest
    "https://obits.azcentral.com/rss/obituaries",
    "https://obits.dallasnews.com/rss/obituaries",
    "https://obits.houstonchronicle.com/rss/obituaries",
    "https://obits.lcsun-news.com/rss/obituaries",
    
    # West
    "https://obits.oregonlive.com/rss/obituaries",
    "https://obits.sacbee.com/rss/obituaries",
    "https://obits.latimes.com/rss/obituaries",
    "https://obits.mercurynews.com/rss/obituaries",
    "https://obits.seattletimes.com/rss/obituaries",
    "https://obits.denverpost.com/rss/obituaries",
    "https://obits.sltrib.com/rss/obituaries",

    # Hawaii & Pacific
    "https://obits.staradvertiser.com/rss/obituaries",
    "https://obits.mauinews.com/rss/obituaries",
    "https://obits.hawaiitribune-herald.com/rss/obituaries",

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
        age INTEGER,
        location TEXT,
        date TEXT,
        source TEXT,
        link TEXT,
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

    # SSDI death records table
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

    # Index for fast name searches
    c.execute('''CREATE INDEX IF NOT EXISTS idx_death_records_last_name 
        ON death_records (last_name)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_death_records_first_name 
        ON death_records (first_name)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_death_records_names 
        ON death_records (last_name, first_name)''')

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


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0"
    }

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        password_hash = hash_password(user.password)
        c.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
                  (user.email, password_hash))
        user_id = c.fetchone()[0]
        conn.commit()
        access_token = create_access_token(data={"sub": user_id})
        return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM users WHERE email = %s", (user.email,))
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
        # Delete notifications first
        c.execute("""
            DELETE FROM notifications 
            WHERE user_id = %s
        """, (user_id,))
        # Delete watchlist items
        c.execute("DELETE FROM watchlist WHERE user_id = %s", (user_id,))
        # Delete user
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
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
                "id": row[0],
                "name": row[1],
                "location": row[2],
                "dob": row[3],
                "status": row[4],
                "created_at": str(row[5])
            })
        return items


@app.post("/watchlist")
async def add_to_watchlist(item: WatchlistItem, user_id: int = Depends(get_current_user)):
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
async def remove_from_watchlist(item_id: int, user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE watchlist SET status = 'deleted' WHERE id = %s AND user_id = %s",
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

        # Search obituaries table
        query = "SELECT * FROM obituaries WHERE name ILIKE %s"
        params = [f"%{search.name}%"]
        if search.location:
            query += " AND location ILIKE %s"
            params.append(f"%{search.location}%")
        query += " ORDER BY scraped_at DESC LIMIT 10"
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
                "source": row[5],
                "link": row[6],
                "confidence": confidence
            })

        # Search SSDI death records
        name_parts = search.name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            ssdi_query = """
                SELECT id, first_name || ' ' || last_name as full_name,
                       NULL as age, state, death_date, source, NULL as link,
                       birth_date
                FROM death_records
                WHERE last_name ILIKE %s AND first_name ILIKE %s
            """
            ssdi_params = [f"%{last_name}%", f"%{first_name}%"]
            if search.birth_year:
                ssdi_query += " AND birth_date LIKE %s"
                ssdi_params.append(f"{search.birth_year}%")
            ssdi_query += " ORDER BY death_date DESC LIMIT 10"
            c.execute(ssdi_query, ssdi_params)
            for row in c.fetchall():
                confidence = calculate_confidence(
                    search.name, row[1], search.location, row[3])
                results.append({
                    "id": row[0] + 1000000,
                    "name": row[1],
                    "age": None,
                    "location": row[3],
                    "date": row[4],
                    "source": "Social Security Death Index",
                    "link": None,
                    "confidence": confidence
                })

        return results


def calculate_confidence(search_name: str, found_name: str,
                         search_loc: Optional[str], found_loc: Optional[str]) -> str:
    search_name = search_name.lower()
    found_name = found_name.lower()
    if search_name == found_name:
        if search_loc and found_loc and search_loc.lower() in found_loc.lower():
            return "high"
        return "medium"
    if search_name in found_name or found_name in search_name:
        return "medium"
    return "low"


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
            ORDER BY n.created_at DESC
            LIMIT 50
        """, (user_id,))
        notifications = []
        for row in c.fetchall():
            notifications.append({
                "id": row[0],
                "name": row[3],
                "message": row[1],
                "created_at": str(row[2]),
                "link": row[4]
            })
        return notifications


# ── SSDI LOADER ───────────────────────────────────────────────────────────────

@app.post("/admin/load-ssdi")
async def load_ssdi_data(file_path: str = "ssdi.csv"):
    """
    Load SSDI data from a CSV file into the death_records table.
    Call this endpoint after uploading the SSDI file to the server.
    SSDI CSV format: SSN, Last Name, First Name, DOB, DOD, State, Zip
    """
    import csv
    count = 0
    try:
        with get_db() as conn:
            c = conn.cursor()
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                batch = []
                for row in reader:
                    if len(row) < 5:
                        continue
                    try:
                        last_name = row[1].strip().title()
                        first_name = row[2].strip().title()
                        birth_date = row[3].strip()
                        death_date = row[4].strip()
                        state = row[5].strip() if len(row) > 5 else None
                        zip_code = row[6].strip() if len(row) > 6 else None
                        if last_name and first_name and death_date:
                            batch.append((first_name, last_name, birth_date,
                                          death_date, state, zip_code))
                            count += 1
                        if len(batch) >= 1000:
                            psycopg2.extras.execute_values(c, """
                                INSERT INTO death_records 
                                (first_name, last_name, birth_date, death_date, state, zip_code)
                                VALUES %s ON CONFLICT DO NOTHING
                            """, batch)
                            conn.commit()
                            batch = []
                    except Exception:
                        continue
                if batch:
                    psycopg2.extras.execute_values(c, """
                        INSERT INTO death_records
                        (first_name, last_name, birth_date, death_date, state, zip_code)
                        VALUES %s ON CONFLICT DO NOTHING
                    """, batch)
                    conn.commit()
        return {"message": f"Loaded {count} SSDI records successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404,
                            detail=f"File {file_path} not found on server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── BACKGROUND TASKS ──────────────────────────────────────────────────────────

def scrape_obituaries():
    print(f"[{datetime.now()}] Starting obituary scrape...")
    with get_db() as conn:
        c = conn.cursor()
        for feed_url in OBITUARY_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                print(f"Feed has {len(feed.entries)} entries")
                for entry in feed.entries[:50]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    name = extract_name_from_title(title)
                    if not name:
                        continue
                    c.execute("SELECT id FROM obituaries WHERE link = %s", (link,))
                    if c.fetchone():
                        continue
                    age = extract_age(title)
                    location = extract_location(title)
                    c.execute("""
                        INSERT INTO obituaries (name, age, location, date, source, link)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (name, age, location, published, feed_url, link))
                conn.commit()
                print(f"Processed {feed_url}")
            except Exception as e:
                print(f"Error scraping {feed_url}: {e}")
        check_watchlist_matches()


def extract_name_from_title(title: str) -> Optional[str]:
    if not title or len(title) < 3:
        return None
    title = title.strip()
    title = re.sub(r'\s+', ' ', title)
    if 3 < len(title) < 100:
        return title
    return None


def extract_age(text: str) -> Optional[int]:
    match = re.search(r'\b(\d{1,3})\b', text)
    if match:
        age = int(match.group(1))
        if 0 < age < 120:
            return age
    return None


def extract_location(text: str) -> Optional[str]:
    match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s+[A-Z]{2})', text)
    if match:
        return match.group(1)
    return None


def check_watchlist_matches():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM watchlist WHERE status = 'active'")
        watchlist_items = c.fetchall()
        for watch in watchlist_items:
            query = "SELECT * FROM obituaries WHERE name ILIKE %s"
            params = [f"%{watch[2]}%"]
            if watch[3]:
                query += " AND location ILIKE %s"
                params.append(f"%{watch[3]}%")
            c.execute(query, params)
            matches = c.fetchall()
            for obit in matches:
                c.execute("""
                    SELECT id FROM notifications
                    WHERE watchlist_id = %s AND obituary_id = %s
                """, (watch[0], obit[0]))
                if not c.fetchone():
                    message = f"Possible match found: {obit[1]} in {obit[3] or 'unknown location'}"
                    c.execute("""
                        INSERT INTO notifications (user_id, watchlist_id, obituary_id, message)
                        VALUES (%s, %s, %s, %s)
                    """, (watch[1], watch[0], obit[0], message))
                    print(f"Created notification for user {watch[1]}: {message}")
        conn.commit()


def run_scheduler():
    schedule.every(1).hours.do(scrape_obituaries)
    while True:
        schedule.run_pending()
        time.sleep(60)


# ── STARTUP ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0"
    }

@app.get("/admin/stats")
async def get_stats():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM obituaries")
        obit_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM death_records")
        death_count = c.fetchone()[0]
        c.execute("SELECT name, date, source FROM obituaries ORDER BY scraped_at DESC LIMIT 5")
        recent = c.fetchall()
        return {
            "obituaries": obit_count,
            "death_records": death_count,
            "most_recent": [{"name": r[0], "date": r[1], "source": r[2]} for r in recent]
        }

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Background scheduler started")
    threading.Thread(target=scrape_obituaries, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
