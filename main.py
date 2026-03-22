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
import httpx
import urllib.request
import urllib.parse
import json as json_lib
from contextlib import contextmanager

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "alerts@memorywatch.app"

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
    # Hawaii and Alaska
    "https://www.legacy.com/obituaries/staradvertiser/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/adn/services/rss.ashx?recentdate=3",
    # Canada
    "https://www.legacy.com/obituaries/theglobeandmail/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/thestar/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/vancouversun/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/calgaryherald/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/ottawacitizen/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/montrealgazette/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/edmontonjournal/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/obituaries/windsorstar/services/rss.ashx?recentdate=3",
    # UK
    "https://www.legacy.com/uk/obituaries/yourlocalpaper-uk/services/rss.ashx?recentdate=3",
    # Australia
    "https://www.legacy.com/au/obituaries/smh/services/rss.ashx?recentdate=3",
    "https://www.legacy.com/au/obituaries/theage/services/rss.ashx?recentdate=3",
    # New Zealand
    "https://www.legacy.com/obituaries/nzherald/services/rss.ashx?recentdate=3",
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
        email_sent BOOLEAN DEFAULT FALSE,
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
    c.execute('''ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS name_normalized TEXT''')
    c.execute('''ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS obit_text TEXT''')
    c.execute('''ALTER TABLE obituaries ADD COLUMN IF NOT EXISTS link TEXT''')
    c.execute('''ALTER TABLE notifications ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_obituaries_name ON obituaries (name)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_obituaries_name_normalized ON obituaries (name_normalized)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_death_records_last_name ON death_records (last_name)''')
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
        name = f"{parts[1].strip()} {parts[0].strip()}"
    name = re.sub(r"\b\w+'\w+\b", lambda m: m.group(0).title(), name)
    return name.title()


def send_email_notification(to_email: str, watchlist_name: str, obit_name: str, obit_location: str, obit_link: str):
    if not RESEND_API_KEY:
        print(f"Email not configured - skipping email to {to_email}")
        return False
    try:
        location_text = obit_location or "Unknown"
        link_text = f'<p><a href="{obit_link}">Read more</a></p>' if obit_link else ""
        html_content = f"""
        <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #7c3aed;">Memory Watch Alert</h2>
            <p>We found a possible match for​​​​​​​​​​​​​​​​
