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
    c.execute("UPDATE watchlist SET is_deceased = FALSE WHERE is_deceased IS NULL")
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
    # Use action API with redirects - bypasses summary cache, gets current article data
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": name,
        "prop": "extracts|pageprops|categories|info",
        "exintro": "true",
        "explaintext": "true",
        "redirects": "1",
        "inprop": "url",
        "cllimit": "50",
        "format": "json"
    })
    url = "https://en.wikipedia.org/w/api.php?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "MemoryWatch/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json_lib.loads(resp.read().decode())

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return {}

    page = list(pages.values())[0]
    if "missing" in page:
        return {}

    title = page.get("title", name)
    extract = page.get("extract", "")

    # Check categories for death - "2026 deaths", "2025 deaths" etc.
    categories = [c.get("title", "") for c in page.get("categories", [])]
    death_year_from_cat = None
    for cat in categories:
        m = re.search(r"(\d{4}) deaths", cat)
        if m:
            death_year_from_cat = m.group(1)
            break

    death_from_category = any(
        any(word in cat.lower() for word in ["deaths", "murdered", "executed"])
        for cat in categories
    )

    # Check for disambiguation
    page_type = "standard"
    if "disambiguation" in page.get("pageprops", {}):
        page_type = "disambiguation"
    elif "(disambiguation)" in title:
        page_type = "disambiguation"

    # Build summary description from extract
    description = ""
    if extract:
        first_sent = extract.split(".")[0]
        description = first_sent[:150] if first_sent else ""

    # Also try summary API for thumbnail and birth/death dates
    thumbnail = None
    birth_date = None
    death_date_summary = None
    try:
        sum_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
        sum_req = urllib.request.Request(sum_url, headers={"User-Agent": "MemoryWatch/1.0"})
        with urllib.request.urlopen(sum_req, timeout=10) as sum_resp:
            sum_data = json_lib.loads(sum_resp.read().decode())
            thumb = sum_data.get("thumbnail")
            thumbnail = thumb.get("source") if thumb else None
            birth_date = sum_data.get("birth_date")
            death_date_summary = sum_data.get("death_date")
            if sum_data.get("description"):
                description = sum_data.get("description")
    except Exception:
        pass

    # Use death_date from summary if available, otherwise from categories
    death_date = death_date_summary or death_year_from_cat

    return {
        "title": title,
        "extract": extract,
        "description": description,
        "type": page_type,
        "death_date": death_date,
        "death_from_category": death_from_category,
        "thumbnail": thumbnail,
        "birth_date": birth_date,
    }

def normalize_name_for_wiki(name: str) -> str:
    # Add period after single-letter middle initials if missing
    # "Robert S Mueller" -> "Robert S. Mueller"
    words = name.strip().split()
    result = []
    for i, word in enumerate(words):
        if len(word) == 1 and word.isalpha() and i > 0 and i < len(words) - 1:
            result.append(word + ".")
        else:
            result.append(word)
    return " ".join(result)

def fetch_wiki_data_smart(name: str) -> dict:
    # Try direct lookup - if resolves cleanly, use it
    data = fetch_wiki_data(name)
    if data.get("type") != "disambiguation" and data.get("extract"):
        return data
    # If disambiguation, use Wikipedia search to find best match
    # but require last name to match to avoid false positives
    name_parts = [p for p in name.strip().split() if p.replace(".", "")]
    last_name = name_parts[-1].lower().replace(".", "") if name_parts else ""
    first_name = name_parts[0].lower() if name_parts else ""
    print("[wiki_smart] Resolving disambiguation for: " + name + " (last=" + last_name + ")")
    try:
        search_url = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(name) + "&srlimit=8&format=json&origin=*"
        req = urllib.request.Request(search_url, headers={"User-Agent": "MemoryWatch/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            search_data = json_lib.loads(resp.read().decode())
        results = search_data.get("query", {}).get("search", [])
        for result in results:
            title = result.get("title", "")
            title_lower = title.lower()
            # Skip disambiguation pages
            if "(disambiguation)" in title_lower:
                continue
            # Must contain last name
            if last_name and last_name not in title_lower:
                continue
            # Must contain first name -- prevents Michael Blatty matching William Blatty
            if first_name and first_name not in title_lower:
                print("[wiki_smart] Skipping " + title + " - first name mismatch (want " + first_name + ")")
                continue
            try:
                candidate = fetch_wiki_data(title)
                if candidate.get("type") == "disambiguation":
                    continue
                if not candidate.get("extract"):
                    continue
                print("[wiki_smart] Resolved " + name + " -> " + title)
                return candidate
            except Exception:
                continue
    except Exception as e:
        print("[wiki_smart] Search failed: " + str(e))
    # Could not resolve - return original disambiguation data
    print("[wiki_smart] Could not resolve: " + name)
    return data


def extract_full_death_date(data: dict) -> str:
    import re as _re
    month_names = "January|February|March|April|May|June|July|August|September|October|November|December"
    full_date_pattern = "(?:" + month_names + r") \d{1,2}, \d{4}"
    extract = data.get("extract", "")
    description = data.get("description", "")
    # Try extract text first - most reliable source for full date
    matches = _re.findall(full_date_pattern, extract)
    if len(matches) >= 2:
        return matches[-1]  # Last date = death date
    if len(matches) == 1:
        first_sentence = extract.split(".")[0]
        if _re.search(r"died|death|passed|\u2013|\u2014", first_sentence, _re.IGNORECASE):
            return matches[0]
    # Try death_date field - only use if it looks like a full date not just a year
    death_date = data.get("death_date", "")
    if death_date and _re.search(full_date_pattern, str(death_date)):
        return str(death_date)
    # Fall back to year from description or category
    m = _re.search(r"\d{4}\s*[\u2013\u2014-]+\s*(\d{4})", description)
    if m:
        return m.group(1)
    m = _re.search(r"\d{4}\s*[\u2013\u2014-]+\s*(\d{4})", extract.split(".")[0] if extract else "")
    if m:
        return m.group(1)
    if death_date:
        return str(death_date)
    return data.get("death_year_from_cat", "") or ""

def is_deceased_from_wiki(data: dict) -> bool:
    extract = data.get("extract", "")
    description = data.get("description", "")
    death_date = data.get("death_date", None)
    page_type = data.get("type", "")
    death_from_category = data.get("death_from_category", False)

    if page_type == "disambiguation":
        return False
    # Death year in category (e.g. "2026 deaths") is most reliable signal
    if death_from_category:
        return True
    if death_date:
        return True
    first_sentence = extract.split(".")[0] if extract else ""
    if re.search(r"\(\d{4}\s*[\u2013\u2014-]+\s*\d{4}\)", first_sentence):
        return True
    if re.search(r"\(\d{4}\s*[\u2013\u2014-]+\s*\d{4}\)", description):
        return True
    if re.search(r"\([^)]*born\s+\w+\s+\d+,\s+\d{4}\)", first_sentence):
        return False
    if re.search(r"(died|death|passed away|deceased)", extract, re.IGNORECASE):
        return True
    if re.search(r"(died|death|deceased)", description, re.IGNORECASE):
        return True
    return False

def search_legacy_oneoff(name: str) -> list:
    """
    One-off Legacy.com search - hits their search page directly.
    Falls back to searching our local scraped DB if Legacy is unavailable.
    """
    results = []

    # Try Legacy.com search directly
    try:
        parts = name.strip().split()
        first = parts[0] if parts else name
        last = parts[-1] if len(parts) > 1 else ""
        search_url = (
            "https://www.legacy.com/obituaries/search?firstName=" +
            urllib.parse.quote(first) +
            "&lastName=" + urllib.parse.quote(last)
        )
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # Extract obit entries from the HTML using simple patterns
            import re as _re
            # Look for JSON-LD structured data
            json_ld_matches = _re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, _re.DOTALL)
            for match in json_ld_matches[:5]:
                try:
                    obj = json_lib.loads(match)
                    if isinstance(obj, list):
                        for item in obj:
                            if item.get("@type") in ["Person", "Obituary"]:
                                results.append({
                                    "name": item.get("name", name),
                                    "date": item.get("deathDate", ""),
                                    "location": item.get("address", {}).get("addressLocality", "") if isinstance(item.get("address"), dict) else "",
                                    "link": item.get("url", search_url),
                                    "obit_text": item.get("description", "")
                                })
                    elif isinstance(obj, dict) and obj.get("@type") in ["Person", "Obituary"]:
                        results.append({
                            "name": obj.get("name", name),
                            "date": obj.get("deathDate", ""),
                            "location": obj.get("address", {}).get("addressLocality", "") if isinstance(obj.get("address"), dict) else "",
                            "link": obj.get("url", search_url),
                            "obit_text": obj.get("description", "")
                        })
                except Exception:
                    continue
            if results:
                print("Legacy direct search found " + str(len(results)) + " results for " + name)
                return results[:5]
    except Exception as e:
        print("Legacy direct search error: " + str(e))

    # Fallback: search our local scraped DB
    try:
        from contextlib import contextmanager as _cm
        normalized = normalize_name(name)
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT name, location, date, link, obit_text FROM obituaries WHERE name ILIKE %s OR name_normalized ILIKE %s ORDER BY scraped_at DESC LIMIT 5",
                ("%" + name + "%", "%" + normalized + "%")
            )
            for row in c.fetchall():
                results.append({
                    "name": row[0] or name,
                    "date": row[2] or "",
                    "location": row[1] or "",
                    "link": row[3] or "",
                    "obit_text": row[4] or ""
                })
        if results:
            print("Legacy DB fallback found " + str(len(results)) + " results for " + name)
    except Exception as e:
        print("Legacy DB fallback error: " + str(e))

    return results

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

app = FastAPI(title="Memory Watch API", version="1.5.6")

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
        "version": "1.5.5"
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

        # If already deceased with stored bio, skip re-checking Wikipedia
        if was_deceased:
            c.execute("SELECT wikipedia_description, death_year FROM watchlist WHERE id = %s", (watch_id,))
            stored = c.fetchone()
            if stored and stored[0]:
                print("[refresh] " + watch_name + " already deceased with bio - fetching fresh thumbnail/dates")
                # Fetch thumbnail and full dates from summary API
                stored_thumbnail = None
                stored_birth = None
                stored_death_full = stored[1]
                try:
                    sum_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(watch_name)
                    sum_req = urllib.request.Request(sum_url, headers={"User-Agent": "MemoryWatch/1.0"})
                    with urllib.request.urlopen(sum_req, timeout=10) as sum_resp:
                        sum_data = json_lib.loads(sum_resp.read().decode())
                    thumb = sum_data.get("thumbnail")
                    stored_thumbnail = thumb.get("source") if thumb else None
                    stored_birth = sum_data.get("birth_date")
                    if sum_data.get("death_date"):
                        stored_death_full = sum_data.get("death_date")
                except Exception as e:
                    print("[refresh] Summary fetch error for " + watch_name + ": " + str(e))
                return {
                    "id": watch_id, "name": watch_name, "is_deceased": True,
                    "wikipedia_description": stored[0], "death_year": stored_death_full,
                    "death_date": stored_death_full, "description": "",
                    "thumbnail": stored_thumbnail, "birth_date": stored_birth,
                    "newly_deceased": False, "legacy_results": []
                }

        wiki_ok = False
        extract = ""
        description = ""
        death_date = None
        thumbnail = None
        birth_date = None
        is_deceased = False

        try:
            normalized_watch_name = normalize_name_for_wiki(watch_name)
            print("[refresh] Smart lookup for: " + normalized_watch_name + " (stored: " + watch_name + ")")
            wiki_data = fetch_wiki_data_smart(normalized_watch_name)
            extract = wiki_data.get("extract", "")
            description = wiki_data.get("description", "")
            death_date = extract_full_death_date(wiki_data)
            if wiki_data.get("thumbnail"):
                thumbnail = wiki_data["thumbnail"].get("source")
            birth_date = wiki_data.get("birth_date", None)
            is_deceased = is_deceased_from_wiki(wiki_data)
            wiki_ok = True
            print("[refresh] " + watch_name + " is_deceased=" + str(is_deceased) + " type=" + str(wiki_data.get("type")))
        except Exception as e:
            print("[refresh] Wikipedia fetch failed for " + watch_name + ": " + str(e))
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
                death_info = (" Died: " + str(death_date)) if death_date else ("" if not extract_full_death_date(wiki_data) else " Died: " + extract_full_death_date(wiki_data))
                message = "Wikipedia reports " + watch_name + " has passed away." + death_info
                c.execute("""
                    INSERT INTO notifications (user_id, watchlist_id, obituary_id, message, email_sent)
                    VALUES (%s, %s, 1, %s, %s)
                """, (user_id, watch_id, message, False))
                conn.commit()
                print("[refresh] Notification created for " + watch_name + death_info)
                if user_email:
                    wiki_link = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(watch_name)
                    sent = send_email_notification(user_email, watch_name, watch_name, None, wiki_link)
                    if sent:
                        c.execute(
                            "UPDATE notifications SET email_sent = TRUE WHERE watchlist_id = %s AND message LIKE %s",
                            (watch_id, "%Wikipedia%"))
                        conn.commit()

        # Normalize thumbnail to string URL
        if isinstance(thumbnail, dict):
            thumbnail = thumbnail.get("source")
        print("[refresh] Result: " + watch_name + " is_deceased=" + str(is_deceased) + " death_date=" + str(death_date) + " thumbnail=" + str(thumbnail is not None))
        return {
            "id": watch_id,
            "name": watch_name,
            "is_deceased": is_deceased,
            "wikipedia_description": extract,
            "death_year": death_date,
            "death_date": death_date,
            "description": description,
            "thumbnail": thumbnail,
            "birth_date": birth_date,
            "newly_deceased": is_deceased and not was_deceased,
            "legacy_results": legacy_results
        }

@app.delete("/notifications/{notif_id}")
async def delete_notification(notif_id: int, user_id: int = Depends(get_current_user)):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM notifications WHERE id = %s AND user_id = %s", (notif_id, user_id))
            conn.commit()
        return {"deleted": True}
    except Exception as e:
        print("Delete notification error: " + str(e))
        return {"deleted": False}

@app.get("/admin/test-refresh/{name}")
async def test_refresh(name: str):
    """Test endpoint - checks Wikipedia for a name and returns raw result. No auth required."""
    try:
        data = fetch_wiki_data(name)
        is_deceased = is_deceased_from_wiki(data)
        return {
            "name": name,
            "is_deceased": is_deceased,
            "death_date": data.get("death_date"),
            "description": data.get("description"),
            "extract_first_sentence": (data.get("extract") or "").split(".")[0],
            "type": data.get("type"),
            "wiki_ok": True
        }
    except Exception as e:
        return {"name": name, "wiki_ok": False, "error": str(e)}

@app.get("/ssdi/search")
async def ssdi_search(name: str, birth_year: str = None, user_id: int = Depends(get_current_user)):
    """
    Search the SSA Death Master File via Google BigQuery.
    Dataset: fiat-fiendum:ssdmf (111M records, deaths through 2014)
    Free public dataset, no certification required.
    """
    try:
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not google_api_key:
            print("[dmf] No GOOGLE_API_KEY set")
            return {"name": name, "results": [], "count": 0}

        # Parse name into first/last
        parts = name.strip().split()
        first = parts[0].upper() if parts else name.upper()
        last = parts[-1].upper() if len(parts) > 1 else ""

        # Build BigQuery SQL query
        # Table: fiat-fiendum.ssdmf.ssdmf
        # Fields: fname, lname, dob, dod, state
        if last:
            query = (
                "SELECT fname, lname, dob, dod, state "
                "FROM `fiat-fiendum.ssdmf.ssdmf` "
                "WHERE UPPER(lname) = @lname "
                "AND UPPER(fname) LIKE @fname "
                "LIMIT 20"
            )
            query_params = [
                {"name": "lname", "parameterType": {"type": "STRING"}, "parameterValue": {"value": last}},
                {"name": "fname", "parameterType": {"type": "STRING"}, "parameterValue": {"value": first + "%"}},
            ]
        else:
            query = (
                "SELECT fname, lname, dob, dod, state "
                "FROM `fiat-fiendum.ssdmf.ssdmf` "
                "WHERE UPPER(fname) LIKE @fname "
                "LIMIT 20"
            )
            query_params = [
                {"name": "fname", "parameterType": {"type": "STRING"}, "parameterValue": {"value": first + "%"}},
            ]

        # Add birth year filter if provided
        if birth_year:
            query = query.replace("LIMIT 20", "AND dob LIKE @birth_year LIMIT 20")
            query_params.append({
                "name": "birth_year",
                "parameterType": {"type": "STRING"},
                "parameterValue": {"value": birth_year + "%"}
            })

        # Call BigQuery REST API
        bq_url = "https://bigquery.googleapis.com/bigquery/v2/projects/memorywatch-dmf/queries?key=" + google_api_key
        payload = json_lib.dumps({
            "query": query,
            "queryParameters": query_params,
            "parameterMode": "NAMED",
            "useLegacySql": False,
            "timeoutMs": 10000
        }).encode()

        req = urllib.request.Request(
            bq_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json_lib.loads(resp.read().decode())

        results = []
        rows = data.get("rows", [])
        schema = data.get("schema", {}).get("fields", [])
        field_names = [f["name"] for f in schema]

        for row in rows:
            values = [v.get("v", "") for v in row.get("f", [])]
            record = dict(zip(field_names, values))
            fname = (record.get("fname") or "").strip().title()
            lname = (record.get("lname") or "").strip().title()
            dob = (record.get("dob") or "").strip()
            dod = (record.get("dod") or "").strip()
            state = (record.get("state") or "").strip()

            # Filter under-18 deaths
            if dob and dod:
                try:
                    birth_yr = int(dob[:4]) if len(dob) >= 4 else 0
                    death_yr = int(dod[:4]) if len(dod) >= 4 else 0
                    if birth_yr and death_yr and (death_yr - birth_yr) < 18:
                        continue
                except Exception:
                    pass

            # Format dates YYYYMMDD -> readable
            def fmt_date(d):
                if not d or len(d) < 8: return d
                try: return d[4:6].lstrip("0") + "/" + d[6:8].lstrip("0") + "/" + d[:4]
                except: return d

            results.append({
                "name": (fname + " " + lname).strip(),
                "birth_date": fmt_date(dob),
                "death_date": fmt_date(dod),
                "state": state,
                "source": "SSA Death Master File"
            })

        print("[dmf] " + name + " -> " + str(len(results)) + " results")
        return {"name": name, "results": results, "count": len(results)}

    except Exception as e:
        print("[dmf] Search error for " + name + ": " + str(e))
        return {"name": name, "results": [], "count": 0}

@app.get("/legacy/search")
async def legacy_search(name: str, user_id: int = Depends(get_current_user)):
    # Legacy search mothballed pending partnership response
    # Preserved for future reactivation
    # try:
    #     normalized = normalize_name(name)
    #     results = search_legacy_oneoff(normalized)
    #     return {"name": normalized, "results": results or [], "count": len(results or [])}
    # except Exception as e:
    #     print("Legacy search error: " + str(e))
    return {"name": name, "results": [], "count": 0}

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
        # NOTE: location not used as a filter - our scraped data has unreliable location fields
        # birth_year filter kept as it is date-based and more reliable
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
            SELECT n.id, n.message, n.created_at, w.name,
                   COALESCE(o.link, '') as link, n.watchlist_id
            FROM notifications n
            JOIN watchlist w ON n.watchlist_id = w.id
            LEFT JOIN obituaries o ON n.obituary_id = o.id
            WHERE n.user_id = %s
            ORDER BY n.created_at DESC LIMIT 50
        """, (user_id,))
        notifications = []
        for row in c.fetchall():
            notifications.append({
                "id": row[0], "name": row[3],
                "message": row[1], "created_at": str(row[2]),
                "link": row[4] or "",
                "watchlist_id": row[5]
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
            AND (w.is_deceased = FALSE OR w.is_deceased IS NULL)
        """)
        watchlist_items = c.fetchall()
        updated = 0
        notified = 0
        for watch in watchlist_items:
            watch_id, user_id, watch_name, user_email, was_deceased = watch
            try:
                normalized_name = normalize_name_for_wiki(watch_name)
                data = fetch_wiki_data_smart(normalized_name)
                if data.get("type") == "disambiguation":
                    continue
                extract = data.get("extract", "")
                death_date = extract_full_death_date(data)
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
                        death_info = (" Died: " + str(death_date)) if death_date else ("" if not extract_full_death_date(data) else " Died: " + extract_full_death_date(data))
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
