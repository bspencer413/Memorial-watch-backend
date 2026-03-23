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
import schedule
import threading
import time
import re
import httpx
import urllib.request
import urllib.parse
import json as json_lib
from contextlib import contextmanager

# import feedparser  # suspended - scraping paused

SECRET_KEY = os.environ.get("SECRET_KEY", "memorial-watch-secret-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "alerts@memorywatch.app"

# OBITUARY_FEEDS suspended - scraping paused, code preserved below
# OBITUARY_FEEDS = [
# "https://www.legacy.com/obituaries/nhregister/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/bostonglobe/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/nytimes/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/philly/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/washingtonpost/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/baltimoresun/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/courant/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/pressherald/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/newsday/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/buffalonews/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/syracuse/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/timesunion/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/providencejournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/delawareonline/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/app/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/northjersey/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/nj/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/poconorecord/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/citizensvoice/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/timesleader/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/pittsburghpostgazette/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/fredericksburg/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/roanoke/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/richmond/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/orlandosentinel/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/miamiherald/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/charlotteobserver/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/ajc/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/tennessean/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/nola/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/sunherald/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/clarionledger/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/tallahassee/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/jacksonville/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/tampabay/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/heraldonline/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/thestate/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/islandpacket/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/newsobserver/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/greensboro/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/kentucky/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/courier-journal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/huntsville/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/al/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/arkansasonline/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/chicagotribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/freep/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/startribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/indystar/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/stltoday/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/kansascity/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/cleveland/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/omaha/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/dispatch/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/cincinnati/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/dayton/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/akron/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/toledo/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/journalsentinel/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/madison/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/greenbaypressgazette/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/postcrescent/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/lansingstatejournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/grandrapids/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/southbendtribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/jconline/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/fortwayne/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/evansville/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/siouxcityjournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/desmoinesregister/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/duluthnewstribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/rapidcityjournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/argusleader/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/bismarcktribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/grandforksherald/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/azcentral/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/dallasnews/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/houstonchronicle/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/expressnews/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/abqjournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/tulsaworld/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/oklahoman/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/lubbockonline/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/caller/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/elpasotimes/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/latimes/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/sfgate/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/oregonlive/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/seattletimes/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/denverpost/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/sltrib/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/sacbee/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/fresnobee/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/modbee/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/mercedsunstar/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/thenewstribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/spokesman/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/idahostatesman/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/montanastandard/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/greatfallstribune/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/billingsgazette/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/nevadaappeal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/rgj/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/reviewjournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/coloradoan/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/gjsentinel/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/wyomingfacts/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/staradvertiser/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/adn/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/theglobeandmail/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/thestar/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/vancouversun/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/calgaryherald/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/ottawacitizen/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/montrealgazette/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/edmontonjournal/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/windsorstar/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/uk/obituaries/yourlocalpaper-uk/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/au/obituaries/smh/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/au/obituaries/theage/services/rss.ashx?recentdate=3",
# "https://www.legacy.com/obituaries/nzherald/services/rss.ashx?recentdate=3",
# ]

DB_HOST = "dpg-d6qhp3ngi27c73a3ivag-a.oregon-postgres.render.com"
DB_USER = "memorial_watch_db_user"
DB_PASS = "9IkXRdY8NcZSKy0yw5b7viPdtIrVIITR"
DB_NAME = "memorial_watch_db"
DATABASE_URL = "postgresql://" + DB_USER + ":" + DB_PASS + "@" + DB_HOST + "/" + DB_NAME

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS watchlist (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        location TEXT,
        dob TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS obituaries (
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
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        watchlist_id INTEGER NOT NULL,
        obituary_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        sent BOOLEAN DEFAULT FALSE,
        email_sent BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (watchlist_id) REFERENCES watchlist (id),
        FOREIGN KEY (obituary_id) REFERENCES obituaries (id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS death_records (
        id SERIAL PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        birth_date TEXT,
        death_date TEXT,
        state TEXT,
        zip_code TEXT,
        source TEXT DEFAULT 'SSDI',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS name_normalized TEXT")
    c.execute("ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS obit_text TEXT")
    c.execute("ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS link TEXT")
    c.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE")
    c.execute("ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS is_deceased BOOLEAN DEFAULT FALSE")
    c.execute("ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS wikipedia_description TEXT")
    c.execute("ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS death_year TEXT")
    c.execute("ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS wiki_last_checked TIMESTAMP")
    c.execute("CREATE INDEX IF NOT EXISTS idx_obituaries_name ON obituaries (name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_obituaries_name_normalized ON obituaries (name_normalized)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_death_records_last_name ON death_records (last_name)")
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
    if not name:
        return name
    name = name.strip()
    if ',' in name:
        parts = name.split(',', 1)
        name = parts[1].strip() + " " + parts[0].strip()
    name = re.sub(r"\b\w+'\w+\b", lambda m: m.group(0).title(), name)
    return name.title()

def send_email_notification(to_email: str, watchlist_name: str, obit_name: str, obit_location: str, obit_link: str):
    if not RESEND_API_KEY:
        print("Email not configured - skipping email to " + to_email)
        return False
    try:
        location_text = obit_location or "Unknown"
        link_text = '<p><a href="' + str(obit_link) + '">Read more</a></p>' if obit_link else ""
        html_content = (
            '<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px;">'
            '<h2 style="color: #7c3aed;">Memory Watch Alert</h2>'
            '<p>We found a possible match for <strong>' + watchlist_name + '</strong> on your watchlist.</p>'
            '<p><strong>Name:</strong> ' + obit_name + '</p>'
            '<p><strong>Location:</strong> ' + location_text + '</p>'
            + link_text +
            '<hr style="border: 1px solid #e5e7eb; margin: 20px 0;">'
            '<p style="color: #6b7280; font-size: 12px;">You are receiving this because you added '
            + watchlist_name + ' to your Memory Watch watchlist. '
            'To manage your watchlist, visit <a href="https://memorywatch.app">memorywatch.app</a></p>'
            '</div>'
        )
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + RESEND_API_KEY, "Content-Type": "application/json"},
            json={
                "from": FROM_EMAIL,
                "to": [to_email],
                "subject": "Memory Watch Alert: " + watchlist_name,
                "html": html_content
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print("Email error: " + str(e))
        return False

def fetch_wiki_data(name: str) -> dict:
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(name)
    req = urllib.request.Request(url, headers={"User-Agent": "MemoryWatch/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json_lib.loads(resp.read().decode())

def is_deceased_from_wiki(data: dict) -> bool:
    extract = data.get("extract", "")
    description = data.get("description", "")
    death_date = data.get("death_date", None)
    page_type = data.get("type", "")
    if page_type == "disambiguation":
        return False
    if death_date:
        return True
    first_sentence = extract.split(".")[0] if extract else ""
    if re.search(r"\(\d{4}\s*[\u2013\u2014-]+\s*\d{4}\)", first_sentence):
        return True
    if re.search(r"\(\d{4}\s*[\u2013\u2014-]+\s*\d{4}\)", description):
        return True
    if re.search(r"\([^)]*born\s+\w+\s+\d+,\s+\d{4}\)", first_sentence):
        return False
    if re.search(r"\b(died|death|passed away|deceased)\b", extract, re.IGNORECASE):
        return True
    if re.search(r"\b(died|death|deceased)\b", description, re.IGNORECASE):
        return True
    return False

def search_legacy_oneoff(name: str) -> list:
    """
    One-off Legacy.com search by name.
    Uses their RSS search feed - same format as our scraper feeds.
    Returns list of obit dicts with name, date, location, link, obit_text.
    """
    try:
        name_encoded = urllib.parse.quote(name)
        url = "https://www.legacy.com/api/_frontend/search?firstName=" + urllib.parse.quote(name.split()[0] if name.split() else name) + "&lastName=" + urllib.parse.quote(name.split()[-1] if len(name.split()) > 1 else "") + "&type=obituary&limit=5"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json_lib.loads(resp.read().decode())
            results = []
            entries = data.get("entries", data.get("results", data.get("obituaries", [])))
            for entry in entries[:5]:
                results.append({
                    "name": entry.get("name", entry.get("fullName", name)),
                    "date": entry.get("deathDate", entry.get("publishDate", "")),
                    "location": entry.get("locationName", entry.get("city", "")),
                    "link": entry.get("url", entry.get("obitUrl", "")),
                    "obit_text": entry.get("snippet", entry.get("summary", ""))
                })
            return results
    except Exception as e:
        print("Legacy one-off search error: " + str(e))
        return []

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
    is_deceased: Optional[bool] = False
    wikipedia_description: Optional[str] = None
    death_year: Optional[str] = None

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

app = FastAPI(title="Memory Watch API", version="1.4.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

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

def calculate_confidence(search_name, found_name, search_loc, found_loc):
    search_name = search_name.lower()
    found_name = found_name.lower()
    if search_name == found_name:
        if search_loc and found_loc and search_loc.lower() in found_loc.lower():
            return "high"
        return "medium"
    if search_name in found_name or found_name in search_name:
        return "medium"
    return "low"

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

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.4.4"
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
            "most_recent": [{"name": r[0], "date": r[1], "source": r[2]} for r in recent],
            "scraping": "suspended"
        }

@app.get("/admin/wiki-check-now")
async def wiki_check_now():
    threading.Thread(target=check_wikipedia_watchlist, daemon=True).start()
    return {"message": "Wikipedia watchlist check started"}

# Scraping endpoint suspended - code preserved
# @app.get("/admin/scrape-now")
# async def scrape_now():
#     threading.Thread(target=scrape_obituaries, daemon=True).start()
#     return {"message": "Scrape started"}

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
        c.execute("SELECT id, password_hash FROM users WHERE email = %s", (user.email,))
        result = c.fetchone()
        if not result or not verify_password(user.password, result[1]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = create_access_token(data={"sub": result[0]})
        return {"access_token": access_token, "token_type": "bearer"}

@app.delete("/account")
async def delete_account(user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM watchlist WHERE user_id = %s", (user_id,))
        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return {"message": "Account permanently deleted"}

@app.get("/watchlist", response_model=List[WatchlistResponse])
async def get_watchlist(user_id: int = Depends(get_current_user)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, location, dob, status, created_at,
                   is_deceased, wikipedia_description, death_year
            FROM watchlist
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))
        items = []
        for row in c.fetchall():
            items.append({
                "id": row[0], "name": row[1], "location": row[2],
                "dob": row[3], "status": row[4], "created_at": str(row[5]),
                "is_deceased": row[6] or False,
                "wikipedia_description": row[7],
                "death_year": row[8]
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
        c.execute(
            "UPDATE watchlist SET status = 'deleted' WHERE id = %s AND user_id = %s",
            (item_id, user_id))
        conn.commit()
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Removed from watchlist"}

@app.get("/watchlist/{item_id}/refresh")
async def refresh_watchlist_item(item_id: int, user_id: int = Depends(get_current_user)):
    """Live refresh - checks Wikipedia + Legacy for latest status. Called when user taps a name."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT w.id, w.name, w.is_deceased, u.email
            FROM watchlist w
            JOIN users u ON w.user_id = u.id
            WHERE w.id = %s AND w.user_id = %s AND w.status = 'active'
        """, (item_id, user_id))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Watchlist item not found")
        watch_id, watch_name, was_deceased, user_email = row
        wiki_ok = False
        extract = ""
        description = ""
        death_date = None
        thumbnail = None
        birth_date = None
        is_deceased = False

        try:
            wiki_data = fetch_wiki_data(watch_name)
            extract = wiki_data.get("extract", "")
            description = wiki_data.get("description", "")
            death_date = wiki_data.get("death_date", None)
            if wiki_data.get("thumbnail"):
                thumbnail = wiki_data["thumbnail"].get("source")
            birth_date = wiki_data.get("birth_date", None)
            is_deceased = is_deceased_from_wiki(wiki_data)
            wiki_ok = True
            print("[refresh] " + watch_name + " wiki_ok=" + str(wiki_ok) + " is_deceased=" + str(is_deceased))
        except Exception as e:
            print("[refresh] Wikipedia fetch failed for " + watch_name + ": " + str(e))
            # Do not default to False if wiki fails - keep was_deceased value
            is_deceased = was_deceased or False

        # Check Legacy one-off
        legacy_results = search_legacy_oneoff(watch_name)

        # If Legacy finds an obit and wiki didn't catch death, mark deceased
        if legacy_results and not is_deceased:
            is_deceased = True
            print("[refresh] Legacy obit found for " + watch_name)

        # Always update the watchlist row if wiki succeeded
        if wiki_ok or legacy_results:
            c.execute("""
                UPDATE watchlist
                SET is_deceased = %s,
                    wikipedia_description = %s,
                    death_year = %s,
                    wiki_last_checked = %s
                WHERE id = %s
            """, (is_deceased, extract[:2000] if extract else None, death_date, datetime.utcnow(), watch_id))
            conn.commit()

        # Create notification if deceased and no notification exists yet for this person
        # Use is_deceased (current state) not was_deceased comparison, to catch cases
        # where DB was stale (person died but DB not yet updated)
        if is_deceased:
            c.execute(
                "SELECT id FROM notifications WHERE watchlist_id = %s AND message LIKE %s",
                (watch_id, "%Wikipedia%"))
            if not c.fetchone():
                death_info = " Died: " + str(death_date) if death_date else ""
                message = "Wikipedia reports " + watch_name + " has passed away." + death_info
                c.execute("""
                    INSERT INTO notifications (user_id, watchlist_id, obituary_id, message, email_sent)
                    VALUES (%s, %s, 1, %s, %s)
                """, (user_id, watch_id, message, False))
                conn.commit()
                print("[refresh] Notification created for " + watch_name)
                if user_email:
                    wiki_link = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(watch_name)
                    sent = send_email_notification(user_email, watch_name, watch_name, None, wiki_link)
                    if sent:
                        c.execute(
                            "UPDATE notifications SET email_sent = TRUE WHERE watchlist_id = %s AND message LIKE %s",
                            (watch_id, "%Wikipedia%"))
                        conn.commit()

        return {
            "id": watch_id,
            "name": watch_name,
            "is_deceased": is_deceased,
            "wikipedia_description": extract,
            "death_year": death_date,
            "description": description,
            "thumbnail": thumbnail,
            "birth_date": birth_date,
            "newly_deceased": is_deceased and not was_deceased,
            "legacy_results": legacy_results
        }

@app.get("/legacy/search")
async def legacy_search(name: str, user_id: int = Depends(get_current_user)):
    """One-off Legacy.com search by name."""
    normalized = normalize_name(name)
    results = search_legacy_oneoff(normalized)
    return {"name": normalized, "results": results, "count": len(results)}

@app.post("/search", response_model=List[ObituaryResult])
async def search_obituaries(search: ObituarySearch):
    """Search our local obituaries DB - kept for backwards compatibility."""
    with get_db() as conn:
        c = conn.cursor()
        results = []
        name = search.name.strip()
        if not name:
            return results
        search_normalized = normalize_name(name)
        query = """SELECT id, name, name_normalized, age, location, date, source, link, obit_text
                   FROM obituaries WHERE name ILIKE %s OR name_normalized ILIKE %s"""
        params = ["%" + name + "%", "%" + search_normalized + "%"]
        if search.location:
            query += " AND location ILIKE %s"
            params.append("%" + search.location + "%")
        if search.birth_year:
            query += " AND date LIKE %s"
            params.append("%" + search.birth_year + "%")
        query += " ORDER BY scraped_at DESC LIMIT 20"
        c.execute(query, params)
        for row in c.fetchall():
            try:
                confidence = calculate_confidence(name, row[1] or "", search.location, row[4])
                results.append({
                    "id": row[0], "name": row[1] or "",
                    "age": row[3], "location": row[4], "date": row[5],
                    "source": "Legacy", "link": row[7],
                    "obit_text": row[8] if len(row) > 8 else None,
                    "confidence": confidence
                })
            except Exception as e:
                print("Error processing search result: " + str(e))
                continue
        return results

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

def check_wikipedia_watchlist():
    """Background job - runs every 6 hours. Checks Wikipedia for all watchlist entries."""
    print("[" + str(datetime.now()) + "] Starting Wikipedia watchlist check...")
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT w.id, w.user_id, w.name, u.email, w.is_deceased
            FROM watchlist w
            JOIN users u ON w.user_id = u.id
            WHERE w.status = 'active'
        """)
        watchlist_items = c.fetchall()
        updated = 0
        notified = 0
        for watch in watchlist_items:
            watch_id, user_id, watch_name, user_email, was_deceased = watch
            try:
                data = fetch_wiki_data(watch_name)
                if data.get("type") == "disambiguation":
                    continue
                extract = data.get("extract", "")
                death_date = data.get("death_date", None)
                is_deceased = is_deceased_from_wiki(data)
                c.execute("""
                    UPDATE watchlist
                    SET is_deceased = %s,
                        wikipedia_description = %s,
                        death_year = %s,
                        wiki_last_checked = %s
                    WHERE id = %s
                """, (is_deceased, extract[:2000] if extract else None, death_date, datetime.utcnow(), watch_id))
                conn.commit()
                updated += 1
                if is_deceased:
                    c.execute(
                        "SELECT id FROM notifications WHERE watchlist_id = %s AND message LIKE %s",
                        (watch_id, "%Wikipedia%"))
                    if not c.fetchone():
                        death_info = " Died: " + str(death_date) if death_date else ""
                        message = "Wikipedia reports " + watch_name + " has passed away." + death_info
                        c.execute("""
                            INSERT INTO notifications (user_id, watchlist_id, obituary_id, message, email_sent)
                            VALUES (%s, %s, 1, %s, %s)
                        """, (user_id, watch_id, message, False))
                        conn.commit()
                        notified += 1
                        if user_email:
                            wiki_link = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(watch_name)
                            sent = send_email_notification(user_email, watch_name, watch_name, None, wiki_link)
                            if sent:
                                c.execute(
                                    "UPDATE notifications SET email_sent = TRUE WHERE watchlist_id = %s AND message LIKE %s",
                                    (watch_id, "%Wikipedia%"))
                                conn.commit()
                time.sleep(0.5)
            except Exception as e:
                print("Wiki check error for " + watch_name + ": " + str(e))
                continue
    print("[" + str(datetime.now()) + "] Wikipedia check complete. " + str(updated) + " updated, " + str(notified) + " notified.")

# SCRAPER CODE SUSPENDED - preserved for future re-activation
# def scrape_obituaries():
#     import feedparser
#     print("[" + str(datetime.now()) + "] Starting obituary scrape...")
#     total = 0
#     with get_db() as conn:
#         c = conn.cursor()
#         for feed_url in OBITUARY_FEEDS:
#             try:
#                 feed = feedparser.parse(feed_url)
#                 count = 0
#                 for entry in feed.entries:
#                     title = " ".join(entry.get("title", "").strip().split())
#                     link = entry.get("link", "")
#                     published = entry.get("published", "")
#                     obit_text = entry.get("summary", "") or entry.get("description", "")
#                     obit_text = re.sub(r"<[^>]+>", "", obit_text).strip()
#                     if not title or len(title) < 3:
#                         continue
#                     if link:
#                         c.execute("SELECT id FROM obituaries WHERE link = %s", (link,))
#                         if c.fetchone():
#                             continue
#                     name_normalized = normalize_name(title)
#                     age = extract_age(title)
#                     location = extract_location(title)
#                     c.execute("""
#                         INSERT INTO obituaries (name, name_normalized, age, location, date, source, link, obit_text)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#                     """, (title, name_normalized, age, location, published, feed_url, link, obit_text))
#                     count += 1
#                 conn.commit()
#                 total += count
#                 print("  " + feed_url + ": " + str(count) + " new entries")
#             except Exception as e:
#                 print("  ERROR " + feed_url + ": " + str(e))
#     print("[" + str(datetime.now()) + "] Scrape complete. " + str(total) + " new obituaries added.")
#     check_watchlist_matches()

# def check_watchlist_matches():
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute("""
#             SELECT w.id, w.user_id, w.name, u.email
#             FROM watchlist w
#             JOIN users u ON w.user_id = u.id
#             WHERE w.status = 'active'
#         """)
#         watchlist_items = c.fetchall()
#         for watch in watchlist_items:
#             watch_id, user_id, watch_name, user_email = watch
#             watch_normalized = normalize_name(watch_name)
#             c.execute("""SELECT id, name, location, link FROM obituaries
#                 WHERE name ILIKE %s OR name_normalized ILIKE %s""",
#                 ("%" + watch_name + "%", "%" + watch_normalized + "%"))
#             matches = c.fetchall()
#             for obit in matches:
#                 obit_id, obit_name, obit_location, obit_link = obit
#                 c.execute(
#                     "SELECT id FROM notifications WHERE watchlist_id = %s AND obituary_id = %s",
#                     (watch_id, obit_id))
#                 if not c.fetchone():
#                     message = "Possible match found: " + obit_name + " in " + (obit_location or "unknown location")
#                     c.execute("""
#                         INSERT INTO notifications (user_id, watchlist_id, obituary_id, message, email_sent)
#                         VALUES (%s, %s, %s, %s, %s)
#                     """, (user_id, watch_id, obit_id, message, False))
#                     conn.commit()
#                     if user_email:
#                         sent = send_email_notification(user_email, watch_name, obit_name, obit_location, obit_link)
#                         if sent:
#                             c.execute(
#                                 "UPDATE notifications SET email_sent = TRUE WHERE watchlist_id = %s AND obituary_id = %s",
#                                 (watch_id, obit_id))
#                             conn.commit()

def run_scheduler():
    schedule.every(6).hours.do(check_wikipedia_watchlist)
    # schedule.every(15).minutes.do(scrape_obituaries)  # suspended
    while True:
        schedule.run_pending()
        time.sleep(60)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Background scheduler started (wiki-check: 6hr, scraping: suspended)")
    threading.Thread(target=check_wikipedia_watchlist, daemon=True).start()
    print("Initial Wikipedia watchlist check started")
    # threading.Thread(target=scrape_obituaries, daemon=True).start()  # suspended

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
