import os
import io
import re
import time
import sqlite3
import asyncio
import random
import string
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.http import Route
from dotenv import load_dotenv
from aiohttp import web

# ==============================================================================
# 1. SERWER KEEP-ALIVE DLA RENDER.COM (UTRZYMANIE BOTA 24/7)
# ==============================================================================
async def handle(request):
    return web.Response(text="Hexully Sh0p Bot is online and running 24/7.")

async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Serwer WWW Keep-Alive aktywny na porcie {port}")

# ==============================================================================
# 2. KONFIGURACJA GŁÓWNA, KANAŁY, STATYSTYKI VC, KATEGORIE I RANGI
# ==============================================================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN', '').strip().strip('"').strip("'")

SHOP_NAME = "👑 | Hexully Sh0p™"

# ID Kanałów Głosowych Statystyk
VC_TRANSAKCJE_ID = 1539238523218173982          # 📊・Transakcje: X PLN
VC_CZLONKOWIE_ID = 1539238525956919318          # 👤〢członków➔X
VC_KLIENCI_ID = 1539238528720961609             # 👱‍♂️〢klienci➔X
VC_ZAMOWIENIA_ID = 1539238532390850590          # 🎁〢zamówień➔X

# ID Kanałów Tekstowych
WELCOME_CHANNEL_ID = 123456789012345678         # ZMIEŃ NA ID KANAŁU POWITALNI
LEGIT_CHECK_CHANNEL_ID = 1539238571083436052    # Kanał Legit Check (+rep oraz licznik 💜・legit・checki➔X)
DZIENNE_LC_CHANNEL_ID = 1539238564926197872     # Kanał Dzienne LC
TICKET_LOGS_CHANNEL_ID = 1539238547557449808    # Kanał Logi Ticketów (Transkrypty)

# ID Kategorii Ticketów
CATEGORY_ZAKUP_ID = 1539238501982146661         # Kategoria dla: Zakup Produktu
CATEGORY_POMOC_ID = 1539238503378980965         # Kategoria dla: Pomoc / Reklamacja / Rekrutacja

# ID Rangi Sprzedawcy (Realizatora) oraz parametry rozliczeń tygodniowych
ROLE_SPRZEDAWCA_ID = 1539238412865900554        # Każdy z tą rangą pojawia się w /adminrozliczenia
SELLER_COMMISSION_RATE = 0.30                   # 30% tygodniowo swoich zarobków dla Zarządu
SELLER_MIN_WEEKLY_PLN = 3.00                    # Minimum 3.00 PLN tygodniowo do wpłaty

# ID Rang Klientów (Progi wydatków)
ROLE_KLIENT_NORMAL = 1539238431513649277        # Normalny Klient (> 0 PLN)
ROLE_KLIENT_100 = 1539238429790052424           # Klient 100+ (>= 100 PLN)
ROLE_KLIENT_300 = 1539238428766511195           # Klient 300+ (>= 300 PLN)
ROLE_KLIENT_500 = 1539238427655147521           # Klient 500+ (>= 500 PLN)
ROLE_KLIENT_1000 = 1539238426098925579          # Klient 1000+ (>= 1000 PLN)

CLIENT_ROLE_TIERS = [
    (1000.0, ROLE_KLIENT_1000),
    (500.0, ROLE_KLIENT_500),
    (300.0, ROLE_KLIENT_300),
    (100.0, ROLE_KLIENT_100),
    (0.01, ROLE_KLIENT_NORMAL),
]

ALL_CLIENT_ROLE_IDS = [
    ROLE_KLIENT_NORMAL,
    ROLE_KLIENT_100,
    ROLE_KLIENT_300,
    ROLE_KLIENT_500,
    ROLE_KLIENT_1000,
]

# Link do kanału regulaminu
REGULAMIN_URL = "https://discord.com/channels/123456789/123456789"

# Kolor przewodni paska bocznego (FIOLETOWY we wszystkich panelach V2 i Embedach!)
THEME_COLOR = 0x9b30ff

BANNER_WELCOME = "https://media.discordapp.net/attachments/1559940184206745660/1559940264427266169/hexully_witamy.png?ex=6ad38a15&is=6ad23895&hm=898bfc4951437b1d9495975cf57608b2863320755be1267a6b9e03a57a6cb352&=&format=webp&quality=lossless&width=640&height=225"
BANNER_VOUCH = "https://media.discordapp.net/attachments/1559940184206745660/1559940252867498115/hexully_vouch.png?ex=6ad38a12&is=6ad23892&hm=f70216eef63d4a48c75d3196a43e47b3e0cb2ae6b59e7032c85c09f8c30b87cd&=&format=webp&quality=lossless"
BANNER_TICKET = "https://media.discordapp.net/attachments/1559940184206745660/1559940241962438749/hexully_ticket.png?ex=6ad38a0f&is=6ad2388f&hm=c3b9cff841857424d8c15710d45b57f4ba62d3c852eac25c175b237d088b401d&=&format=webp&quality=lossless"
BANNER_CLIENT = "https://media.discordapp.net/attachments/1559940184206745660/1559940235385774151/hexully_panel_klienta.png?ex=6ad38a0e&is=6ad2388e&hm=dc54b91f562fbae09e634b630dce9a7e10e1756291cd67b7f3c406c2faa3f3aa&=&format=webp&quality=lossless"
BANNER_CENNIK = "https://media.discordapp.net/attachments/1559940184206745660/1559940216691626046/hexully_cennik.png?ex=6ad38a09&is=6ad23889&hm=fcd0ed65c969569ec61aabcbd9f4624549a83758b098684cf93ad3e5ca50fc6f&=&format=webp&quality=lossless"
BANNER_CZY_LEGIT = "https://media.discordapp.net/attachments/1559940184206745660/1559940226854690867/hexully_czy_legit.png?ex=6ad38a0c&is=6ad2388c&hm=85c8a8772760236d87a85e2330f757aaf1bff4497f055ff30047a72de77a2fd5&=&format=webp&quality=lossless"
BANNER_SZUKAJ = "https://media.discordapp.net/attachments/1559940184206745660/1559940283356029070/hexully_wyszukaj_1.png?ex=6ad38a19&is=6ad23899&hm=ccf6ed5151bd6f169ae89905ca49c838bda25a4d2c6680950acb799bb1b9cb96&=&format=webp&quality=lossless"
BANNER_OPINIA = "https://media.discordapp.net/attachments/1559940184206745660/1559940294794022973/hexully_opinia.png?ex=6ad38a1c&is=6ad2389c&hm=eeb5f6bcddca0375d915954fadf144f35954dae9742c447dbb79b9400660bfda&=&format=webp&quality=lossless"

# ==============================================================================
# 3. KATALOG WSZYSTKICH PRODUKTÓW DO WYSZUKIWARKI (/panel_wyszukaj)
# ==============================================================================
PRODUCT_CATALOG = [
    # Oferta Nitro
    {"name": "Nɪtro Boost vɪa Gɪft 1M Bez Gwarancjɪ", "price": "18.00 PLN"},
    {"name": "Nɪtro Boost vɪa Gɪft 1M Z Gwarancja", "price": "24.00 PLN"},
    {"name": "Nɪtro Basɪc vɪa Gɪft 1M", "price": "8.00 PLN"},
    {"name": "Nɪtro Boost vɪa Gɪft 1Y (1 Rok)", "price": "180.00 PLN"},
    {"name": "Nɪtro Boost Promolɪnk 3M (Nɪtro Trɪal)", "price": "10.00 PLN"},
    {"name": "Nɪtro Boost Vɪa CC 1M", "price": "20.00 PLN"},
    {"name": "Nɪtro Boost Vɪa CC 1Y (1 Rok)", "price": "200.00 PLN"},
    {"name": "14x Sɛrvɛr Boosts 1M Bez Gwarancjɪ", "price": "16.00 PLN"},
    {"name": "14x Sɛrvɛr Boosts 1M Z Gwarancja", "price": "18.00 PLN"},
    {"name": "28x Sɛrvɛr Boosts 1M Bez Gwarancjɪ", "price": "26.00 PLN"},
    {"name": "28x Sɛrvɛr Boosts 1M Z Gwarancja", "price": "32.00 PLN"},
    {"name": "14x Sɛrvɛr Boosts 3M Bez Gwarancjɪ", "price": "30.00 PLN"},
    {"name": "14x Sɛrvɛr Boosts 3M Z Gwarancja", "price": "35.00 PLN"},
    {"name": "28x Sɛrvɛr Boosts 3M Bez Gwarancjɪ", "price": "50.00 PLN"},
    {"name": "28x Sɛrvɛr Boosts 3M Z Gwarancja", "price": "55.00 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 20.49 PLN)", "price": "8.19 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 22.49 PLN)", "price": "9.00 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 29.00 PLN)", "price": "11.60 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 35.00 PLN)", "price": "14.00 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 37.99 PLN)", "price": "15.20 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 41.99 PLN)", "price": "16.80 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 48.00 PLN)", "price": "19.20 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 56.99 PLN)", "price": "22.80 PLN"},
    {"name": "Dɛko vɪa Gɪft (Normalnie 66.00 PLN)", "price": "26.40 PLN"},
    {"name": "Random Dɛko vɪa Gɪft", "price": "9.00 PLN"},
    # Oferta Discord
    {"name": "Rɛal Mɛmbɛrs 1k (1000 osób)", "price": "13.00 PLN"},
    {"name": "Onlɪnɛ Mɛmbɛrs 1k (1000 osób)", "price": "18.00 PLN"},
    {"name": "Offlɪnɛ Mɛmbɛrs 1k (1000 osób)", "price": "10.00 PLN"},
    {"name": "Rɛakcjɛ 1k (1000 sztuk)", "price": "18.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2024 (Full Accɛss)", "price": "4.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2023 (Full Accɛss)", "price": "5.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2022 (Full Accɛss)", "price": "7.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2021 (Full Accɛss)", "price": "9.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2020 (Full Accɛss)", "price": "10.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2019 (Full Accɛss)", "price": "14.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2018 (Full Accɛss)", "price": "20.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2017 (Full Accɛss)", "price": "25.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2016 (Full Accɛss)", "price": "54.00 PLN"},
    {"name": "Konto Agɛd Dɪscord 2015 (Full Accɛss)", "price": "230.00 PLN"},
    {"name": "Konto Dɪscord Z Nɪtrɛm Boost 1M", "price": "12.00 PLN"},
    {"name": "Konto Dɪscord Z Nɪtrɛm Boost 3M", "price": "16.00 PLN"},
    # Oferta Streamingowa
    {"name": "Nɛtflɪx 1M (1 Miesiąc)", "price": "8.00 PLN"},
    {"name": "Nɛtflɪx 3M (3 Miesiące)", "price": "10.00 PLN"},
    {"name": "Nɛtflɪx Lyf (Lɪfɛtɪmɛ)", "price": "14.00 PLN"},
    {"name": "Nɛtflɪx Lɪfɛtɪmɛ 4K Plan FA Lyf", "price": "49.99 PLN"},
    {"name": "HboMax 3M (3 Miesiące)", "price": "5.00 PLN"},
    {"name": "HboMax 6M (6 Miesięcy)", "price": "8.00 PLN"},
    {"name": "HboMax Lyf (Na Zawsze)", "price": "12.00 PLN"},
    {"name": "Dɪsnɛy+ Random Sub Lyf", "price": "7.00 PLN"},
    {"name": "Dɪsnɛy+ + Hulu Lyf", "price": "9.00 PLN"},
    {"name": "Dɪsnɛy+ + Hulu + Espn+ Lyf", "price": "11.00 PLN"},
    {"name": "Spotɪfy Prɛmɪum 3M (Full Accɛss)", "price": "9.00 PLN"},
    {"name": "Spotɪfy Prɛmɪum 12M (Full Accɛss)", "price": "27.00 PLN"},
    {"name": "Spotɪfy Prɛmɪum Lyf (Kɛy Na Twoje Konto)", "price": "30.00 PLN"},
    {"name": "Prɪmɛ Vɪdɛo 1M (1 Miesiąc)", "price": "8.00 PLN"},
    {"name": "Prɪmɛ Vɪdɛo 3M (3 Miesiące)", "price": "12.00 PLN"},
    {"name": "Prɪmɛ Vɪdɛo 6M (Full Accɛss)", "price": "15.00 PLN"},
    {"name": "Prɪmɛ Vɪdɛo Lyf (Full Accɛss)", "price": "26.00 PLN"},
    {"name": "Playɛr Bɛz Rɛklam 1M", "price": "8.00 PLN"},
    {"name": "Playɛr Bɛz Rɛklam 3M", "price": "10.00 PLN"},
    {"name": "Playɛr Bɛz Rɛklam 6M", "price": "15.00 PLN"},
    {"name": "Playɛr Bɛz Rɛklam 12M", "price": "18.00 PLN"},
    {"name": "Playɛr Bɛz Rɛklam Lyf", "price": "25.00 PLN"},
    {"name": "Cda Prɛmɪum 1M", "price": "8.00 PLN"},
    {"name": "Cda Prɛmɪum 3M", "price": "14.00 PLN"},
    {"name": "Cda Prɛmɪum Lyf", "price": "22.00 PLN"},
    # Oferta VPN
    {"name": "NσrdVpn 1M (1 Miesiąc)", "price": "7.00 PLN"},
    {"name": "NσrdVpn 3M (3 Miesiące)", "price": "10.00 PLN"},
    {"name": "NσrdVpn 6M (6 Miesięcy)", "price": "13.00 PLN"},
    {"name": "NσrdVpn 12M (12 Miesięcy)", "price": "16.00 PLN"},
    {"name": "IpVanɪsh 1M (1 Miesiąc)", "price": "6.00 PLN"},
    {"name": "IpVanɪsh 12M (12 Miesięcy)", "price": "10.00 PLN"},
    {"name": "ExprɛssVpn 1M (1 Miesiąc)", "price": "4.00 PLN"},
    {"name": "ExprɛssVpn 12M (12 Miesięcy)", "price": "7.00 PLN"},
    # Oferta Hazard
    {"name": "Stakɛ LvL 2 (Full Access - Lɪfɛtɪmɛ)", "price": "4.00 PLN"},
    {"name": "Stakɛ LvL 2 (Na Twój Email - Lɪfɛtɪmɛ)", "price": "8.00 PLN"},
]

# ==============================================================================
# 4. BAZA DANYCH SQLITE (STATYSTYKI, DZIENNE LC, ROZLICZENIA TYGODNIOWE)
# ==============================================================================
DB_PATH = "hexully_shop.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS client_stats (
            user_id INTEGER PRIMARY KEY,
            total_spent REAL NOT NULL DEFAULT 0.0,
            purchases_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_orders (
            user_id INTEGER PRIMARY KEY,
            amount REAL NOT NULL DEFAULT 0.0,
            product TEXT,
            seller_id INTEGER,
            seller_settled INTEGER NOT NULL DEFAULT 0
        )
    """)
    try:
        c.execute("ALTER TABLE pending_orders ADD COLUMN seller_settled INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_lc (
            date_str TEXT PRIMARY KEY,
            lc_count INTEGER NOT NULL DEFAULT 0,
            total_pln REAL NOT NULL DEFAULT 0.0,
            message_id INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS seller_settlements (
            seller_id INTEGER PRIMARY KEY,
            tx_count INTEGER NOT NULL DEFAULT 0,
            turnover REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def db_get_setting(key: str, default: str = "") -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM shop_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return str(row[0]) if row else default

def db_set_setting(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO shop_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

if not db_get_setting("settlement_period_start", ""):
    db_set_setting("settlement_period_start", datetime.now().strftime("%d.%m.%Y %H:%M"))

def db_increment_setting(key: str, delta: int = 1) -> int:
    current = int(db_get_setting(key, "0") or "0")
    new_val = max(0, current + delta)
    db_set_setting(key, str(new_val))
    return new_val

# --- FUNKCJE BAZODANOWE DLA ROZLICZEŃ TYGODNIOWYCH SPRZEDAWCÓW ---
def calculate_seller_financials(weekly_earnings: float) -> Dict[str, float]:
    """
    Oblicza tygodniowe rozliczenie sprzedawcy:
    - 30% tygodniowo swoich zarobków trafia do Zarządu (minimum 3.00 PLN tygodniowo).
    - 70% tygodniowych zarobków to zysk netto sprzedawcy.
    """
    clean_weekly_earnings = max(0.0, round(float(weekly_earnings), 2))
    raw_weekly_30 = round(clean_weekly_earnings * SELLER_COMMISSION_RATE, 2)
    due_to_owners = max(SELLER_MIN_WEEKLY_PLN, raw_weekly_30)
    seller_net_profit = round(clean_weekly_earnings * (1.0 - SELLER_COMMISSION_RATE), 2)
    return {
        "turnover": clean_weekly_earnings,
        "raw_30": raw_weekly_30,
        "due_to_owners": due_to_owners,
        "net_profit": seller_net_profit,
    }

def db_add_seller_sale(seller_id: int, amount: float):
    if not seller_id or amount <= 0:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    c.execute("SELECT tx_count, turnover FROM seller_settlements WHERE seller_id = ?", (int(seller_id),))
    row = c.fetchone()
    if row:
        new_tx = int(row[0]) + 1
        new_turnover = round(float(row[1]) + float(amount), 2)
        c.execute(
            "UPDATE seller_settlements SET tx_count = ?, turnover = ?, updated_at = ? WHERE seller_id = ?",
            (new_tx, new_turnover, now_str, int(seller_id))
        )
    else:
        c.execute(
            "INSERT INTO seller_settlements (seller_id, tx_count, turnover, updated_at) VALUES (?, 1, ?, ?)",
            (int(seller_id), round(float(amount), 2), now_str)
        )
    conn.commit()
    conn.close()

def db_get_seller_settlement(seller_id: int) -> Dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT tx_count, turnover, updated_at FROM seller_settlements WHERE seller_id = ?", (int(seller_id),))
    row = c.fetchone()
    conn.close()
    tx_count = int(row[0]) if row else 0
    turnover = float(row[1]) if row else 0.0
    updated_at = str(row[2]) if (row and row[2]) else "Brak transakcji"
    fin = calculate_seller_financials(turnover)
    return {
        "seller_id": int(seller_id),
        "tx_count": tx_count,
        "turnover": fin["turnover"],
        "raw_30": fin["raw_30"],
        "due_to_owners": fin["due_to_owners"],
        "net_profit": fin["net_profit"],
        "updated_at": updated_at,
    }

def db_get_all_seller_settlements_map() -> Dict[int, Dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT seller_id, tx_count, turnover, updated_at FROM seller_settlements")
    rows = c.fetchall()
    conn.close()
    result = {}
    for r in rows:
        s_id = int(r[0])
        tx_cnt = int(r[1])
        turn = float(r[2])
        upd = str(r[3]) if r[3] else "Brak"
        fin = calculate_seller_financials(turn)
        result[s_id] = {
            "seller_id": s_id,
            "tx_count": tx_cnt,
            "turnover": fin["turnover"],
            "raw_30": fin["raw_30"],
            "due_to_owners": fin["due_to_owners"],
            "net_profit": fin["net_profit"],
            "updated_at": upd,
        }
    return result

def db_reset_seller_settlements(seller_id: Optional[int] = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if seller_id is not None:
        c.execute("DELETE FROM seller_settlements WHERE seller_id = ?", (int(seller_id),))
    else:
        c.execute("DELETE FROM seller_settlements")
    conn.commit()
    conn.close()
    if seller_id is None:
        db_set_setting("settlement_period_start", datetime.now().strftime("%d.%m.%Y %H:%M"))

# --- FUNKCJE BAZODANOWE DLA KLIENTÓW I STATYSTYK ---
def db_get_client_spent(user_id: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_spent FROM client_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def db_add_client_spent(user_id: int, amount: float) -> float:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_spent, purchases_count FROM client_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    add_val = max(0.0, round(float(amount), 2))
    if row:
        new_total = round(float(row[0]) + add_val, 2)
        new_count = int(row[1]) + 1
        c.execute(
            "UPDATE client_stats SET total_spent = ?, purchases_count = ? WHERE user_id = ?",
            (new_total, new_count, user_id)
        )
    else:
        new_total = add_val
        c.execute(
            "INSERT INTO client_stats (user_id, total_spent, purchases_count) VALUES (?, ?, 1)",
            (user_id, new_total)
        )
    conn.commit()
    conn.close()
    return new_total

def db_set_client_spent(user_id: int, amount: float) -> float:
    new_total = max(0.0, round(float(amount), 2))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM client_stats WHERE user_id = ?", (user_id,))
    if c.fetchone():
        c.execute("UPDATE client_stats SET total_spent = ? WHERE user_id = ?", (new_total, user_id))
    else:
        c.execute(
            "INSERT INTO client_stats (user_id, total_spent, purchases_count) VALUES (?, ?, 1)",
            (user_id, new_total)
        )
    conn.commit()
    conn.close()
    return new_total

def db_get_top_clients(limit: int = 10) -> List[Tuple[int, float]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, total_spent FROM client_stats WHERE total_spent > 0 ORDER BY total_spent DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [(int(r[0]), float(r[1])) for r in rows]

def db_get_global_totals() -> Tuple[float, int, int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(total_spent), 0.0), COUNT(user_id), COALESCE(SUM(purchases_count), 0) FROM client_stats WHERE total_spent > 0 OR purchases_count > 0")
    row = c.fetchone()
    conn.close()
    total_pln = round(float(row[0]), 2) if row else 0.0
    clients_cnt = int(row[1]) if row else 0
    orders_cnt = int(row[2]) if row else 0
    lc_total = int(db_get_setting("total_lc_count", "0") or "0")
    orders_cnt = max(orders_cnt, lc_total)
    return total_pln, clients_cnt, orders_cnt

def db_set_pending_order(user_id: int, amount: float, product: str, seller_id: int, seller_settled: int = 1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO pending_orders (user_id, amount, product, seller_id, seller_settled) VALUES (?, ?, ?, ?, ?)",
        (user_id, round(float(amount), 2), product, seller_id, int(seller_settled))
    )
    conn.commit()
    conn.close()

def db_pop_pending_order(user_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT amount, seller_id, seller_settled FROM pending_orders WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM pending_orders WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return {
            "amount": float(row[0]),
            "seller_id": int(row[1]) if row[1] else None,
            "seller_settled": bool(row[2]),
        }
    conn.close()
    return None

def db_record_daily_lc(amount: float) -> Dict:
    today_str = datetime.now().strftime("%d.%m.%Y")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT lc_count, total_pln, message_id FROM daily_lc WHERE date_str = ?", (today_str,))
    row = c.fetchone()
    if row:
        new_lc = int(row[0]) + 1
        new_pln = round(float(row[1]) + max(0.0, float(amount)), 2)
        c.execute(
            "UPDATE daily_lc SET lc_count = ?, total_pln = ? WHERE date_str = ?",
            (new_lc, new_pln, today_str)
        )
    else:
        new_lc = 1
        new_pln = round(max(0.0, float(amount)), 2)
        c.execute(
            "INSERT INTO daily_lc (date_str, lc_count, total_pln, message_id) VALUES (?, ?, ?, NULL)",
            (today_str, new_lc, new_pln)
        )
    conn.commit()
    conn.close()
    return db_get_daily_lc_summary(today_str)

def db_get_daily_lc_summary(date_str: Optional[str] = None) -> Dict:
    if not date_str:
        date_str = datetime.now().strftime("%d.%m.%Y")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT lc_count, total_pln, message_id FROM daily_lc WHERE date_str = ?", (date_str,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO daily_lc (date_str, lc_count, total_pln, message_id) VALUES (?, 0, 0.0, NULL)", (date_str,))
        conn.commit()
        today_lc, today_pln, msg_id = 0, 0.0, None
    else:
        today_lc, today_pln, msg_id = int(row[0]), float(row[1]), row[2]

    c.execute("SELECT date_str, lc_count FROM daily_lc ORDER BY lc_count DESC LIMIT 1")
    rec_row = c.fetchone()
    conn.close()

    if rec_row and int(rec_row[1]) > 0:
        rec_date, rec_count = str(rec_row[0]), int(rec_row[1])
    else:
        rec_date, rec_count = date_str, today_lc

    missing_to_record = max(0, (rec_count + 1) - today_lc) if today_lc < rec_count else 0

    return {
        "date_str": date_str,
        "lc_count": today_lc,
        "total_pln": today_pln,
        "message_id": int(msg_id) if msg_id else None,
        "record_count": rec_count,
        "record_date": rec_date,
        "missing_lc": missing_to_record,
    }

def db_set_daily_lc_message_id(date_str: str, message_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE daily_lc SET message_id = ? WHERE date_str = ?", (int(message_id), date_str))
    conn.commit()
    conn.close()

def get_client_tier_info(total_spent: float) -> Tuple[Optional[int], float]:
    if total_spent >= 1000.0:
        return ROLE_KLIENT_1000, 0.0
    elif total_spent >= 500.0:
        return ROLE_KLIENT_500, round(1000.0 - total_spent, 2)
    elif total_spent >= 300.0:
        return ROLE_KLIENT_300, round(500.0 - total_spent, 2)
    elif total_spent >= 100.0:
        return ROLE_KLIENT_100, round(300.0 - total_spent, 2)
    elif total_spent > 0.0:
        return ROLE_KLIENT_NORMAL, round(100.0 - total_spent, 2)
    else:
        return None, 100.0

async def sync_member_client_roles(member: discord.Member, total_spent: float) -> Optional[int]:
    target_role_id, _ = get_client_tier_info(total_spent)
    guild = member.guild

    roles_to_remove = []
    target_role_obj = None

    for r_id in ALL_CLIENT_ROLE_IDS:
        role_obj = guild.get_role(r_id)
        if not role_obj:
            continue
        if r_id == target_role_id:
            target_role_obj = role_obj
        else:
            if role_obj in member.roles:
                roles_to_remove.append(role_obj)

    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason=f"Aktualizacja rangi klienta ({total_spent:.2f} PLN)")
        if target_role_obj and target_role_obj not in member.roles:
            await member.add_roles(target_role_obj, reason=f"Awans rangi klienta ({total_spent:.2f} PLN)")
    except Exception as e:
        print(f"⚠️ Błąd podczas nadawania rangi klienta dla {member}: {e}")

    return target_role_id

def parse_amount_from_text(text: str) -> float:
    if not text:
        return 0.0
    matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:pln|zł|zl)', text, flags=re.IGNORECASE)
    if matches:
        try:
            return round(float(matches[-1].replace(',', '.')), 2)
        except ValueError:
            pass
    bracket_matches = re.findall(r'\[\s*(\d+(?:[.,]\d+)?)\s*\]', text)
    if bracket_matches:
        try:
            return round(float(bracket_matches[-1].replace(',', '.')), 2)
        except ValueError:
            pass
    return 0.0

# ==============================================================================
# 5. PAMIĘĆ OPERACYJNA TICKETÓW, LOGÓW I KOLEJKI STATYSTYK KANAŁÓW
# ==============================================================================
ACTIVE_TICKETS = {}          # {user_id: channel_id}
TICKET_TRANSCRIPTS = {}      # {channel_id: [str, ...]}
TICKET_METADATA = {}         # {channel_id: {...}}
LAST_LC_STICKY_MESSAGE_ID = None
CHANNEL_RENAME_COOLDOWN: Dict[int, float] = {}

# ==============================================================================
# 6. BAZA WSZYSTKICH TWOICH EMOTEK Z DEVELOPER PORTAL (STRONY 1-6)
# ==============================================================================
RAW_EMOJIS = {
    # Strona 1-2
    "yes_box": {"name": "yes_box_yes", "id": "1559844176475197470", "animated": False},
    "x": {"name": "x_", "id": "1559844174910726154", "animated": False},
    "wlasciciel": {"name": "Wlasciciel", "id": "1559844173476012112", "animated": False},
    "weryfikacja": {"name": "weryfikacja", "id": "1559844171487903804", "animated": False},
    "verifynoob": {"name": "verifynoob", "id": "1559844169550270559", "animated": False},
    "valide_noir": {"name": "valide_noir", "id": "1559844168170217472", "animated": False},
    "uzytkownik": {"name": "uzytkownik", "id": "1559844166459203584", "animated": False},
    "udostepnij": {"name": "udostepnij", "id": "1559844164806385664", "animated": False},
    "tseller": {"name": "tseller", "id": "1559844163615195206", "animated": False},
    "teamzarzad": {"name": "teamzarzad", "id": "1559844162298445844", "animated": False},
    "supportteam": {"name": "supportteam", "id": "1559844160750493756", "animated": False},
    "strzalka2": {"name": "strzalka2", "id": "1559844159467028510", "animated": False},
    "strzalka": {"name": "strzalka", "id": "1559844158401806376", "animated": False},
    "serce": {"name": "serce", "id": "1559844156984135700", "animated": False},
    "seller": {"name": "seller", "id": "1559844155591491654", "animated": False},
    "reklamacje": {"name": "reklamacje", "id": "1559844154010243082", "animated": False},
    "regulamin": {"name": "regulamin", "id": "1559844152517201982", "animated": False},
    "prezent": {"name": "prezent", "id": "1559844151242268743", "animated": False},
    "portfel": {"name": "portfel", "id": "1559844149996425278", "animated": False},
    "pineska": {"name": "pineska", "id": "1559844148528287836", "animated": False},
    "pieniadze": {"name": "pienidze", "id": "1559844147630972989", "animated": False},
    "pay1": {"name": "pay1", "id": "1559844146527866880", "animated": False},
    "pay": {"name": "Pay", "id": "1559844145340743750", "animated": False},
    "partnerstwo": {"name": "partnerstwo", "id": "1559844144132792440", "animated": False},
    "papier": {"name": "papier", "id": "1559844142920634368", "animated": False},
    "osoba": {"name": "osoba", "id": "1559844141351829524", "animated": False},
    "olowek": {"name": "olowek", "id": "1559844139925774376", "animated": False},
    "no_check": {"name": "NO_check", "id": "1559844138810212382", "animated": False},
    "nitro_nitro": {"name": "Nitro_nitro", "id": "1559844137296076811", "animated": False},
    "nitro_boost": {"name": "nitro_boost", "id": "1559844134624170044", "animated": False},
    "nitro_badge": {"name": "nitro_badge_classic_boost", "id": "1559844132745125918", "animated": False},
    "nitro": {"name": "nitro", "id": "1559844131449217084", "animated": False},
    "megafon": {"name": "megafon", "id": "1559844127837921350", "animated": False},
    "lupa": {"name": "lupa", "id": "1559844124050464768", "animated": False},
    "like": {"name": "like", "id": "1559844119172620298", "animated": False},
    "koszyk": {"name": "koszyk", "id": "1559844118006464522", "animated": False},
    "koperta": {"name": "koperta", "id": "1559844116978864249", "animated": False},
    "konkurs": {"name": "konkurs", "id": "1559844115930292284", "animated": False},
    "klient_500": {"name": "klient_500", "id": "1559844114378399775", "animated": False},
    "klient_250": {"name": "klient_250", "id": "1559844112750878730", "animated": False},
    "klient_100": {"name": "klient_100", "id": "1559844111429799968", "animated": False},
    "klient": {"name": "klient", "id": "1559844110247002173", "animated": False},
    "kalendarz": {"name": "kalendarz", "id": "1559844108812558366", "animated": False},
    "info": {"name": "info", "id": "1559844107466182666", "animated": False},
    "info_red": {"name": "Info", "id": "1559844106094780437", "animated": False},
    "alert": {"name": "horny_minor_alert", "id": "1559844104857325628", "animated": False},
    "hasztag": {"name": "hasztag", "id": "1559844103087329360", "animated": False},
    # Strona 3-6
    "gwiazdka": {"name": "gwiazdka", "id": "1559844101741092925", "animated": False},
    "goat_pin": {"name": "Goat_Pin", "id": "1559844098234388591", "animated": False},
    "goat_owner": {"name": "Goat_Owner", "id": "1559844096254808064", "animated": False},
    "friend": {"name": "friend", "id": "1559844093956198490", "animated": False},
    "dlugopis": {"name": "dlugopis", "id": "1559844092760948756", "animated": False},
    "dislike": {"name": "dislike", "id": "1559844091372642304", "animated": False},
    "dev": {"name": "Dev", "id": "1559844089673945098", "animated": False},
    "crypto": {"name": "crypto", "id": "1559844086767165441", "animated": False},
    "casino_cash": {"name": "Casino_cash", "id": "1559844083198074941", "animated": False},
    "booster": {"name": "booster", "id": "1559844081809756180", "animated": False},
    "blacklist": {"name": "blacklist", "id": "1559844080681353227", "animated": False},
    "admin": {"name": "Admin", "id": "1559844076809887744", "animated": False},
    "chatgpt": {"name": "521605chatgpt", "id": "1559844060938899458", "animated": False},
    "btc": {"name": "99508bitcoin", "id": "1559844046275350629", "animated": False},
    "ltc": {"name": "74062ltc", "id": "1559844038109171722", "animated": False},
    "instagram": {"name": "73238instagram", "id": "1559844036884430858", "animated": False},
    "sol": {"name": "8033solana", "id": "1559843994375299152", "animated": False},
    "usdt": {"name": "7541tetherusdt", "id": "1559843991661318144", "animated": False},
    "eth": {"name": "3031ethereum", "id": "1559843985030119435", "animated": False},
    "paypal": {"name": "_wcx_paypal", "id": "1559843965489127444", "animated": False},
    "applepay": {"name": "25515applepay", "id": "1559844000863748146", "animated": False},
    "netflix": {"name": "51220netflix", "id": "1559844028059615281", "animated": False},
    "spotify": {"name": "35248spotify", "id": "1559844002591936512", "animated": False},
    "disney": {"name": "53408disneyplus", "id": "1559844031310340156", "animated": False},
    "hbomax": {"name": "62970hbomax", "id": "1559844034057343066", "animated": False},
    "youtube": {"name": "54079youtube", "id": "1559844032711098438", "animated": False},
    "primevideo": {"name": "79386primevideo", "id": "1559844039543619675", "animated": False},
    "robux": {"name": "79718robux", "id": "1559844040751452251", "animated": False},
    "box": {"name": "5962box", "id": "1559843989081817108", "animated": False},
    "discord_icon": {"name": "4929discord", "id": "1559843987865739375", "animated": False},
    "nordvpn": {"name": "2493nordvpn", "id": "1559843984187195452", "animated": False},
    "minecraft": {"name": "1491minecraft", "id": "1559843982962331708", "animated": False},
    "gtav": {"name": "1196_gta_v", "id": "1559843981662093403", "animated": False},
    "3osoby": {"name": "3osoby", "id": "1559843971172409515", "animated": False},
}

E = {}

def rebuild_emoji_strings():
    for key, data in RAW_EMOJIS.items():
        prefix = "a" if data.get("animated") else ""
        E[key] = f"<{prefix}:{data['name']}:{data['id']}>"

rebuild_emoji_strings()

def emoji_json(key: str) -> dict:
    data = RAW_EMOJIS[key]
    return {
        "name": data["name"],
        "id": str(data["id"]),
        "animated": bool(data.get("animated", False))
    }

def emoji_partial(key: str) -> discord.PartialEmoji:
    data = RAW_EMOJIS[key]
    return discord.PartialEmoji(
        name=data["name"],
        id=int(data["id"]),
        animated=bool(data.get("animated", False))
    )

def generuj_kod_reklamacji() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def get_payment_options() -> list:
    return [
        {"label": "Blik", "value": "Blik", "emoji": emoji_json("pieniadze")},
        {"label": "PayPal", "value": "PayPal", "emoji": emoji_json("paypal")},
        {"label": "USDT", "value": "USDT", "emoji": emoji_json("usdt")},
        {"label": "LTC", "value": "LTC", "emoji": emoji_json("ltc")},
        {"label": "BTC", "value": "BTC", "emoji": emoji_json("btc")},
        {"label": "SOL", "value": "SOL", "emoji": emoji_json("sol")},
        {"label": "PSC", "value": "PSC", "emoji": emoji_json("portfel")},
        {"label": "MY PSC", "value": "MY PSC", "emoji": emoji_json("pay")},
    ]

def get_star_rating_options() -> list:
    return [
        {"label": "⭐", "value": "1"},
        {"label": "⭐⭐", "value": "2"},
        {"label": "⭐⭐⭐", "value": "3"},
        {"label": "⭐⭐⭐⭐", "value": "4"},
        {"label": "⭐⭐⭐⭐⭐", "value": "5"},
    ]

# ==============================================================================
# 7. WYSYŁANIE I EDYCJA KONTENERÓW DISCORD COMPONENTS V2 (FLAGS: 32768)
# ==============================================================================
async def send_v2_container(bot: commands.Bot, channel_id: int, inner_components: list):
    payload = {
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "accent_color": THEME_COLOR,
                "components": inner_components
            }
        ]
    }
    return await bot.http.request(
        Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id),
        json=payload
    )

async def edit_v2_container(bot: commands.Bot, channel_id: int, message_id: int, inner_components: list):
    payload = {
        "flags": 32768,
        "components": [
            {
                "type": 17,
                "accent_color": THEME_COLOR,
                "components": inner_components
            }
        ]
    }
    return await bot.http.request(
        Route('PATCH', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id, message_id=message_id),
        json=payload
    )

# ==============================================================================
# 8. BEZPIECZNA AKTUALIZACJA NAZW KANAŁÓW GŁOSOWYCH I LICZNIKÓW
# ==============================================================================
async def safe_rename_channel(channel: Optional[discord.abc.GuildChannel], new_name: str, force: bool = False):
    if channel is None:
        return
    if getattr(channel, "name", None) == new_name:
        return

    now = time.time()
    last_time = CHANNEL_RENAME_COOLDOWN.get(channel.id, 0.0)
    if not force and (now - last_time) < 320.0:
        return

    try:
        CHANNEL_RENAME_COOLDOWN[channel.id] = now
        await channel.edit(name=new_name)
    except Exception as e:
        print(f"⚠️ Pominięto zmianę nazwy kanału {channel.id} ({new_name}): {e}")

async def update_all_live_channels(bot: commands.Bot, guild: discord.Guild, force: bool = False):
    if guild is None:
        return

    total_pln, db_clients_cnt, orders_cnt = db_get_global_totals()

    role_holder_ids = set()
    for r_id in ALL_CLIENT_ROLE_IDS:
        r_obj = guild.get_role(r_id)
        if r_obj:
            for m in r_obj.members:
                role_holder_ids.add(m.id)
    clients_count = max(db_clients_cnt, len(role_holder_ids))

    pln_str = f"{int(total_pln)}" if total_pln.is_integer() else f"{total_pln:.2f}"

    # 1. Kanały głosowe
    ch_trans = guild.get_channel(VC_TRANSAKCJE_ID)
    await safe_rename_channel(ch_trans, f"📊・Transakcje: {pln_str} PLN", force=force)

    ch_members = guild.get_channel(VC_CZLONKOWIE_ID)
    await safe_rename_channel(ch_members, f"👤〢członków➔{guild.member_count}", force=force)

    ch_clients = guild.get_channel(VC_KLIENCI_ID)
    await safe_rename_channel(ch_clients, f"👱‍♂️〢klienci➔{clients_count}", force=force)

    ch_orders = guild.get_channel(VC_ZAMOWIENIA_ID)
    await safe_rename_channel(ch_orders, f"🎁〢zamówień➔{orders_cnt}", force=force)

    # 2. Kanały tekstowe z licznikami
    lc_count = int(db_get_setting("total_lc_count", str(orders_cnt)) or "0")
    lc_count = max(lc_count, orders_cnt)
    ch_lc = guild.get_channel(LEGIT_CHECK_CHANNEL_ID)
    await safe_rename_channel(ch_lc, f"💜・legit・checki➔{lc_count}", force=force)

    opinie_ch_id = int(db_get_setting("opinie_channel_id", "0") or "0")
    if opinie_ch_id:
        opinie_count = int(db_get_setting("total_opinie_count", "0") or "0")
        ch_opinie = guild.get_channel(opinie_ch_id)
        await safe_rename_channel(ch_opinie, f"💜・opinie・klientów➔{opinie_count}", force=force)

    legit_ch_id = int(db_get_setting("czy_legit_channel_id", "0") or "0")
    if legit_ch_id:
        legit_votes = int(db_get_setting("total_czy_legit_count", "0") or "0")
        ch_legit = guild.get_channel(legit_ch_id)
        await safe_rename_channel(ch_legit, f"💜・czy・jesteśmy・legit➔{legit_votes}", force=force)

# ==============================================================================
# 9. SYSTEM TRANSKRYPTÓW I LOGÓW TICKETÓW (KANAŁ 1539238547557449808)
# ==============================================================================
async def close_ticket_with_transcript(
    bot: commands.Bot,
    channel: discord.TextChannel,
    closed_by: discord.abc.User,
    reason: str = "Zamknięcie ręczne"
):
    channel_id = channel.id
    meta = TICKET_METADATA.get(channel_id, {})

    owner_id = meta.get("owner_id")
    if not owner_id and channel.topic and "ticket_owner:" in channel.topic:
        try:
            owner_id = int(channel.topic.split("ticket_owner:")[1].split("|")[0])
        except Exception:
            owner_id = None

    owner_mention = f"<@{owner_id}> (`{owner_id}`)" if owner_id else "Nieznany"
    claimed_by_id = meta.get("claimed_by")
    claimed_mention = f"<@{claimed_by_id}>" if claimed_by_id else "Brak (Nieprzejęty)"
    produkt_info = meta.get("produkt", "-")
    kwota_info = meta.get("kwota", "-")
    kod_rek_info = meta.get("kod_reklamacji", "-")

    history_lines = []
    try:
        async for msg in channel.history(limit=500, oldest_first=True):
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content_str = msg.content if msg.content else ""
            if not content_str and msg.embeds:
                content_str = "[Wiadomość Embed]"
            elif not content_str and msg.components:
                content_str = "[Panel / Kontener Components V2]"
            if msg.attachments:
                att_links = ", ".join(a.url for a in msg.attachments)
                content_str += f" [Załączniki: {att_links}]"
            history_lines.append(f"[{time_str}] {msg.author} ({msg.author.id}): {content_str}")
    except Exception as e:
        print(f"Błąd pobierania historii kanału do transkryptu: {e}")

    if not history_lines:
        history_lines = TICKET_TRANSCRIPTS.get(
            channel_id,
            [f"--- Brak zapisanych wiadomości tekstowych w kanale {channel.name} ---"]
        )

    header_txt = (
        f"============================================================\n"
        f"               TRANSKRYPT TICKETA - {SHOP_NAME}\n"
        f"============================================================\n"
        f"Nazwa kanału     : {channel.name} ({channel.id})\n"
        f"Klient (ID)      : {owner_id if owner_id else 'Nieznany'}\n"
        f"Przejęty przez   : {claimed_by_id if claimed_by_id else 'Brak'}\n"
        f"Produkt / Typ    : {produkt_info}\n"
        f"Kwota zamówienia : {kwota_info}\n"
        f"Kod Reklamacji   : {kod_rek_info}\n"
        f"Zamknięty przez  : {closed_by} ({closed_by.id})\n"
        f"Powód zamknięcia : {reason}\n"
        f"Data zamknięcia  : {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"Liczba wiadomości: {len(history_lines)}\n"
        f"============================================================\n\n"
    )
    full_txt = header_txt + "\n".join(history_lines)

    if TICKET_LOGS_CHANNEL_ID:
        logs_channel = bot.get_channel(TICKET_LOGS_CHANNEL_ID)
        if logs_channel is None:
            try:
                logs_channel = await bot.fetch_channel(TICKET_LOGS_CHANNEL_ID)
            except Exception as e:
                print(f"❌ Nie udało się pobrać kanału logów {TICKET_LOGS_CHANNEL_ID}: {e}")

        if logs_channel is not None:
            try:
                log_components = [
                    {
                        "type": 10,
                        "content": f"```\n              {SHOP_NAME} × LOGI TICKETA\n```"
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 10,
                        "content": (
                            f"> {E['koszyk']} ' **Kanał Ticketa:** `{channel.name}` (`{channel.id}`)\n"
                            f"> {E['osoba']} ' **Klient:** {owner_mention}\n"
                            f"> {E['seller']} ' **Obsługujący (Seller):** {claimed_mention}\n"
                            f"> {E['box']} ' **Produkt / Kategoria:** `{produkt_info}`\n"
                            f"> {E['pay']} ' **Kwota:** `{kwota_info}`\n"
                            f"> {E['hasztag']} ' **Kod Reklamacji:** `{kod_rek_info}`\n"
                            f"> {E['weryfikacja']} ' **Zamknięty przez:** {closed_by.mention} (`{closed_by.id}`)\n"
                            f"> {E['kalendarz']} ' **Data zamknięcia:** `{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}`\n"
                            f"> {E['info']} ' **Powód:** `{reason}`"
                        )
                    },
                    {"type": 14, "divider": True, "spacing": 1},
                    {
                        "type": 10,
                        "content": f"-# {E['papier']} © 2026 {SHOP_NAME} × Archiwum Transkryptów"
                    }
                ]
                await send_v2_container(bot, logs_channel.id, log_components)

                transcript_file = discord.File(
                    io.BytesIO(full_txt.encode('utf-8')),
                    filename=f"transkrypt-{channel.name}.txt"
                )
                await logs_channel.send(
                    content=f"{E['papier']} **Pełny zapis rozmowy z ticketa `{channel.name}`:**",
                    file=transcript_file
                )
            except Exception as e:
                print(f"❌ Błąd podczas wysyłania transkryptu na kanał logów: {e}")

    TICKET_TRANSCRIPTS.pop(channel_id, None)
    TICKET_METADATA.pop(channel_id, None)
    for uid, cid in list(ACTIVE_TICKETS.items()):
        if cid == channel_id:
            ACTIVE_TICKETS.pop(uid, None)
            break

    try:
        await channel.delete(reason=reason)
    except Exception as e:
        print(f"Błąd usuwania kanału ticketa: {e}")

# ==============================================================================
# 10. GENERATORY PANELI ROZLICZENIOWYCH SPRZEDAWCÓW (30% TYGODNIOWO SWOICH ZAROBKÓW)
# ==============================================================================
def build_seller_settlement_panel_components():
    """Generuje Panel Rozliczeniowy Sprzedawców (Components V2) z przyciskiem Moje Statystyki."""
    return [
        {
            "type": 10,
            "content": f"```\n        {SHOP_NAME} × PANEL ROZLICZENIOWY\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"### {E['pieniadze']} Panel Rozliczeniowy Sprzedawców\n"
                f"> {E['info']} ' Kanał do wrzucania raportów i sprawdzania swoich tygodniowych statystyk.\n"
                f"> {E['portfel']} ' **Zasady rozliczeń:** **`30%` tygodniowo Twoich zarobków** (**minimum `3.00 PLN` tygodniowo**).\n"
                f"> {E['strzalka']} ' Kliknij przycisk **poniżej** lub wpisz `/rozliczenie`, aby sprawdzić swoje rozliczenie z tego tygodnia!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 1,
                    "custom_id": "seller_my_settlement_btn",
                    "label": "Moje Statystyki",
                    "emoji": emoji_json("pieniadze")
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × System Rozliczeń Tygodniowych"
        }
    ]

def build_seller_individual_settlement_embed(member: discord.abc.User, stats: Dict) -> discord.Embed:
    """Generuje kartę rozliczeniową dla pojedynczego sprzedawcy (30% tygodniowo swoich zarobków)."""
    period_start = db_get_setting("settlement_period_start", "Ostatniego poniedziałku")
    tx_count = stats["tx_count"]
    turnover = stats["turnover"]
    net_profit = stats["net_profit"]
    raw_30 = stats["raw_30"]
    due_to_owners = stats["due_to_owners"]

    if raw_30 < SELLER_MIN_WEEKLY_PLN:
        regula_info = f"`{due_to_owners:.2f} PLN` *(Minimum 3.00 PLN tygodniowo — 30% Twoich zarobków z tygodnia to {raw_30:.2f} PLN)*"
    else:
        regula_info = f"`{due_to_owners:.2f} PLN` *(30% tygodniowo Twoich zarobków)*"

    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n      {SHOP_NAME} × TWOJE ROZLICZENIA (TEN TYDZIEŃ)\n```\n"
        f"{E['kalendarz']} ' **Statystyki od:** `{period_start}`\n"
        f"{E['seller']} ' **Sprzedawca:** {member.mention}\n\n"
        f"**Ilość transakcji:**\n"
        f"**`{tx_count}`**\n\n"
        f"**Łączny obrót (Twoje zarobki w tym tygodniu):**\n"
        f"**`{turnover:.2f} PLN`**\n\n"
        f"**Twój zysk netto (70%):**\n"
        f"**`{net_profit:.2f} PLN`**\n\n"
        f"**Do wpłaty tygodniowo (Zarząd — 30% Twoich zarobków):**\n"
        f"{E['strzalka']} **{regula_info}**\n\n"
        f"-# {E['info']} Ostatnia zrealizowana transakcja: {stats['updated_at']}"
    )
    avatar_url = member.display_avatar.url if hasattr(member, "display_avatar") else None
    embed.set_footer(
        text=f"© 2026 {SHOP_NAME} × Rozliczenia Tygodniowe • Dziś o {datetime.now().strftime('%H:%M')}",
        icon_url=avatar_url
    )
    return embed

def build_admin_all_settlements_embed(guild: discord.Guild) -> discord.Embed:
    """
    Generuje pełny raport dla Właścicieli (/adminrozliczenia):
    Uwzględnia KAŻDĄ osobę posiadającą rangę Sprzedawca (1539238412865900554)
    oraz wylicza 30% tygodniowo z ich zarobków (min. 3.00 PLN tygodniowo).
    """
    period_start = db_get_setting("settlement_period_start", "Ostatniego poniedziałku")
    db_map = db_get_all_seller_settlements_map()

    seller_role = guild.get_role(ROLE_SPRZEDAWCA_ID)
    seller_ids = set(db_map.keys())
    if seller_role:
        for m in seller_role.members:
            if not m.bot:
                seller_ids.add(m.id)

    combined_list = []
    for s_id in seller_ids:
        if s_id in db_map:
            combined_list.append(db_map[s_id])
        else:
            fin = calculate_seller_financials(0.0)
            combined_list.append({
                "seller_id": s_id,
                "tx_count": 0,
                "turnover": fin["turnover"],
                "raw_30": fin["raw_30"],
                "due_to_owners": fin["due_to_owners"],
                "net_profit": fin["net_profit"],
                "updated_at": "Brak",
            })

    combined_list.sort(key=lambda x: (x["turnover"], x["tx_count"]), reverse=True)

    total_sellers = len(combined_list)
    total_tx = sum(item["tx_count"] for item in combined_list)
    total_turnover = round(sum(item["turnover"] for item in combined_list), 2)
    total_due_owners = round(sum(item["due_to_owners"] for item in combined_list), 2)

    embed = discord.Embed(color=THEME_COLOR)

    if not combined_list:
        lista_txt = (
            f"> {E['info']} ' Na serwerze nikt nie posiada jeszcze rangi <@&{ROLE_SPRZEDAWCA_ID}> "
            f"ani zapisanych transakcji w tym tygodniu."
        )
    else:
        wiersze = []
        for idx, item in enumerate(combined_list, start=1):
            s_id = item["seller_id"]
            tx = item["tx_count"]
            obr = item["turnover"]
            netto = item["net_profit"]
            do_oddania = item["due_to_owners"]
            status_tag = "*(min. 3 PLN tygodniowo)*" if item["raw_30"] < SELLER_MIN_WEEKLY_PLN else "*(30% tygodniowych zarobków)*"

            wiersze.append(
                f"**{idx}.** {E['seller']} <@{s_id}>\n"
                f"> • Transakcje: `{tx}` | Zarobki w tygodniu: `{obr:.2f} PLN` | Zysk netto (70%): `{netto:.2f} PLN`\n"
                f"> • {E['strzalka']} **Do wpłaty tygodniowo (Zarząd):** **`{do_oddania:.2f} PLN`** {status_tag}"
            )
        lista_txt = "\n\n".join(wiersze[:25])

    embed.description = (
        f"```\n       {SHOP_NAME} × ROZLICZENIA TYGODNIOWE KADRY\n```\n"
        f"> {E['kalendarz']} ' **Okres tygodniowy od:** `{period_start}`\n"
        f"> {E['teamzarzad']} ' **Ranga Sprzedawcy:** <@&{ROLE_SPRZEDAWCA_ID}> (`{total_sellers} osób`)\n"
        f"> {E['koszyk']} ' **Łącznie transakcji w tygodniu:** `{total_tx}`\n"
        f"> {E['portfel']} ' **Łączne zarobki kadry (Ten Tydzień):** `{total_turnover:.2f} PLN`\n"
        f"> {E['wlasciciel']} ' **ŁĄCZNIE DO ODEBRANIA PRZEZ WŁAŚCICIELI:** **`{total_due_owners:.2f} PLN`**\n"
        f"──────────────────────────────────────────\n"
        f"{lista_txt}"
    )
    icon_url = guild.icon.url if guild and guild.icon else None
    embed.set_footer(
        text=f"© 2026 {SHOP_NAME} × Panel Zarządu (30% tygodniowo / min. 3 PLN) • Reset: /resetujrozliczenia",
        icon_url=icon_url
    )
    return embed

# ==============================================================================
# 11. GENERATORY POZOSTAŁYCH PANELI COMPONENTS V2 I EMBEDÓW
# ==============================================================================

# --- 11.1. POWITALNIA (Components V2) ---
def build_welcome_components(member: discord.Member, guild: discord.Guild):
    avatar_url = member.display_avatar.replace(format="png", size=256).url
    return [
        {
            "type": 10,
            "content": f"```\n               {SHOP_NAME} × NOWA OSOBA\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 9,
            "components": [
                {
                    "type": 10,
                    "content": (
                        f"> {E['osoba']} ' **Hejka** {member.mention}! Miło **Cię** u __nas widzieć__!\n"
                        f"> {E['serce']} ' **Jest** nam __mega mega__ miło, że **wpadłeś**. Rozgość się!"
                    )
                }
            ],
            "accessory": {
                "type": 11,
                "media": {"url": avatar_url}
            }
        },
        {
            "type": 10,
            "content": (
                f"{E['pineska']} ' **Przypominamy**, że __nie przestrzeganie__ się z naszym "
                f"**regulaminem** może wiązać się z __lotą__."
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 9,
            "components": [
                {
                    "type": 10,
                    "content": (
                        f"### {E['regulamin']} ' Sprawdź __nasz__ regulamin\n"
                        f"Zanim __zrobisz__ ticketa **prosimy** - obczaj __nasz__ **regulamin**."
                    )
                }
            ],
            "accessory": {
                "type": 2,
                "style": 5,
                "label": "' Sprawdź Regulamin!",
                "url": REGULAMIN_URL,
                "emoji": emoji_json("lupa")
            }
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "custom_id": "welcome_counter_btn",
                    "disabled": True,
                    "label": f"' Dzięki, że wbiłeś! Jesteś naszym {guild.member_count} użytkownikiem.",
                    "emoji": emoji_json("osoba")
                }
            ]
        },
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_WELCOME}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Nowa Osoba"
        }
    ]

# --- 11.2. LEGIT CHECK (Components V2) ---
def build_legit_check_components():
    return [
        {
            "type": 10,
            "content": f"```\n               {SHOP_NAME} × LEGIT CHECK\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['info']} ' **Wzór:**\n"
                f"`+rep @sᴇʟʟᴇʀ x1 Produkt Jaki Zakupiłeś [Mᴇᴛᴏᴅᴀ Płᴀᴛɴᴏśᴄɪ] [Kwota PLN]`\n\n"
                f"> {E['lupa']} ' **Przykład:**\n"
                f"`+rep @seller x1 Nᴇᴛꜰʟɪx 1 Mɪᴇsɪᴀᴄ Full Warr [BLIK] [7.99 PLN]`"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_VOUCH}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Legit Check"
        }
    ]

# --- 11.3. DZIENNE LC (Kanał 1539238564926197872) ---
def build_daily_lc_embed(summary: Dict) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n        🍁 ' {SHOP_NAME} × DZIENNE LC\n```\n"
        f"> • {E['lupa']} ' **Data:** `{summary['date_str']}`\n"
        f"> • {E['lupa']} ' **Łącznie wystawiono:** `{summary['lc_count']} Lɛgɪt Chɛcków`\n"
        f"> • {E['lupa']} ' **Łączna wartość zamówień:** `{summary['total_pln']:.2f} PLN`\n\n"
        f"> • {E['lupa']} ' **Rekord dzienny:** `{summary['record_count']} LC` *({summary['record_date']})*\n"
        f"> • {E['gwiazdka']} ' **Do rekordu brakuje:** `{summary['missing_lc']} LC`\n\n"
        f"{E['serce']} ' **__Dziękujemy__** za to, że **jesteście z nami!**"
    )
    embed.set_footer(text=f"© 2026 {SHOP_NAME} × Dzienne LC • Dziś o {datetime.now().strftime('%H:%M')}")
    return embed

async def update_or_send_daily_lc_message(bot: commands.Bot, summary: Optional[Dict] = None):
    if not DZIENNE_LC_CHANNEL_ID:
        return
    channel = bot.get_channel(DZIENNE_LC_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DZIENNE_LC_CHANNEL_ID)
        except Exception as e:
            print(f"⚠️ Nie można pobrać kanału Dzienne LC ({DZIENNE_LC_CHANNEL_ID}): {e}")
            return

    if summary is None:
        summary = db_get_daily_lc_summary()

    embed = build_daily_lc_embed(summary)
    msg_id = summary.get("message_id")

    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed)
            return
        except Exception:
            pass

    try:
        new_msg = await channel.send(embed=embed)
        db_set_daily_lc_message_id(summary["date_str"], new_msg.id)
    except Exception as e:
        print(f"⚠️ Błąd wysyłania raportu Dzienne LC: {e}")

# --- 11.4. CZY JESTEŚMY LEGIT (Components V2) ---
def build_czy_legit_components():
    return [
        {
            "type": 10,
            "content": f"```\n            🍁 ' {SHOP_NAME} × CZY JESTEŚMY LEGIT\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['yes_box']} × Uważasz, że **jesteśmy __LEGIT__**? Zostaw reakcję {E['yes_box']} __pod__ **tą wiadomością!**\n"
                f"> {E['x']} × Twierdzisz, że __nie__ **jesteśmy __LEGIT__**? Zareaguj {E['no_check']} __pod__ **tą wiadomością!**\n\n"
                f"> {E['strzalka']} ' **Wystawienie** reakcji {E['no_check']} __bez dowodu__ skutkuje **natychmiastową przerwą na 7 dni**!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_CZY_LEGIT}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Zaznacz Reakcje"
        }
    ]

# --- 11.5. WYSZUKIWANIE PRODUKTÓW (Components V2) ---
def build_search_product_panel_components():
    return [
        {
            "type": 10,
            "content": f"```\n           {SHOP_NAME} × Wyszukiwanie Produktów\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['lupa']} ' **Chcesz** szybko znaleźć konkretny **produkt?**\n"
                f"> **Kliknij w przycisk** poniżej i wpisz co __szukasz__ – wyślemy Ci wszystkie **pasujące ceny!**"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "custom_id": "search_product_btn",
                    "label": "' Kliknij, aby wyszukać produkt",
                    "emoji": emoji_json("lupa")
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_SZUKAJ}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Wyszukiwanie Produktów"
        }
    ]

# --- 11.6. WYSTAW OPINIĘ & OPINIA KLIENTA (Components V2) ---
def build_wystaw_opinie_panel_components():
    return [
        {
            "type": 10,
            "content": f"```\n               🍁 ' {SHOP_NAME} × WYSTAW OPINIĘ\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['strzalka']} ' **Wystawiając** nam __opinię__ dajesz **innym** znać, co Cię u nas **__zadowoliło__**.\n"
                f"> {E['strzalka']} ' **Będziemy super __wdzięczni__** za każdą **__wystawioną__ opinię** – to buduje __zaufanie__ do naszego sklepu!\n"
                f"> {E['strzalka']} ' **Opinię** możesz napisać __klikając__ w przycisk **poniżej**."
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 2,
                    "custom_id": "open_review_modal_btn",
                    "label": "' Kliknij, aby wystawić opinię!",
                    "emoji": emoji_json("info")
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Wystaw Opɪnɪɪ"
        }
    ]

def build_published_review_components(
    user: discord.Member,
    tresc: str,
    poprawic: str,
    jakosc_stars: int,
    czas_stars: int,
    przebieg_stars: int
):
    avatar_url = user.display_avatar.replace(format="png", size=256).url
    stars_j = "⭐" * max(1, min(5, jakosc_stars))
    stars_c = "⭐" * max(1, min(5, czas_stars))
    stars_p = "⭐" * max(1, min(5, przebieg_stars))

    return [
        {
            "type": 10,
            "content": f"```\n                  🍁 ' {SHOP_NAME} × OPINIA\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 9,
            "components": [
                {
                    "type": 10,
                    "content": (
                        f"> {E['osoba']} ' **Twórca Opɪnɪɪ:** {user.mention}\n"
                        f"> {E['info']} ' **Treść:** `{tresc}`\n"
                        f"> {E['strzalka']} ' **Co możemy poprawić:** `{poprawic if poprawic else 'nic'}`"
                    )
                }
            ],
            "accessory": {
                "type": 11,
                "media": {"url": avatar_url}
            }
        },
        {
            "type": 10,
            "content": (
                f"> {E['koszyk']} ' **Jakość Produktow:** `{stars_j}`\n"
                f"> {E['kalendarz']} ' **Czas Realizacji:** `{stars_c}`\n"
                f"> {E['kalendarz']} ' **Przebieg Transakcjɪ:** `{stars_p}`"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_OPINIA}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Opɪnɪɛ Klɪɛntow"
        }
    ]

# --- 11.7. PANEL TICKETÓW (Components V2) ---
def build_tickets_panel_components():
    return [
        {
            "type": 10,
            "content": f"```\n                 {SHOP_NAME} × TICKETY\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['koszyk']} ' **Chcesz zakupić produkt** bądź **potrzebujesz pomocy** od __administracji__? "
                f"Bądź __Twój produkt wygasł__ i chcesz go **wymienić**? Lub **coś innego**?\n\n"
                f"> {E['strzalka']} ' **Skorzystaj** z menu __poniżej__ i wybierz odpowiednią kategorię, a my **zajmiemy się resztą**!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 3,
                    "custom_id": "ticket_category_select",
                    "placeholder": "' Wybierz Interesującą Cię Kategorie Ticketa!",
                    "options": [
                        {
                            "label": "Zakup Produktu",
                            "description": "Stwórz ticket, aby zakupić wybrany produkt!",
                            "value": "zakup",
                            "emoji": emoji_json("koszyk")
                        },
                        {
                            "label": "Pomoc Ogólna",
                            "description": "Potrzebujesz pomocy od administracji? Kliknij tutaj!",
                            "value": "pomoc",
                            "emoji": emoji_json("supportteam")
                        },
                        {
                            "label": "Reklamacja",
                            "description": "Twój produkt wygasł lub nie działa? Zgłoś reklamację!",
                            "value": "reklamacja",
                            "emoji": emoji_json("reklamacje")
                        },
                        {
                            "label": "Rekrutacja",
                            "description": "Chcesz dołączyć do naszej kadry? Złóż podanie!",
                            "value": "rekrutacja",
                            "emoji": emoji_json("partnerstwo")
                        }
                    ]
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_TICKET}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Panel Ticketów"
        }
    ]

# --- 11.8. PANEL KLIENTA + STATYSTYKI I TOPKA ---
def build_client_panel_components():
    return [
        {
            "type": 10,
            "content": f"```\n              {SHOP_NAME} × PANEL KLIENTA\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['portfel']} ' **Ciekawi Cię** ile wydałeś **u nas** łącznie? Albo **chcesz zobaczyć** topkę **naszych** __najlepszych__ klientów?\n\n"
                f"> {E['strzalka']} ' **Wybierz** interesującą Cię **opcję** __poniżej__!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 3,
                    "custom_id": "client_panel_select",
                    "placeholder": "' Wybierz opcję którą jesteś zainteresowany!",
                    "options": [
                        {
                            "label": "Sprawdź Swoje Statystyki",
                            "description": "Sprawdź ile wydałeś u nas!",
                            "value": "statystyki",
                            "emoji": emoji_json("osoba")
                        },
                        {
                            "label": "Topka Najlepszych Klientów",
                            "description": "Zobacz ranking osób, które wydały najwięcej!",
                            "value": "topka",
                            "emoji": emoji_json("klient_500")
                        },
                        {
                            "label": "Wylosuj Zniżkę",
                            "description": "Odbierz lub wylosuj swój kod rabatowy!",
                            "value": "znizka",
                            "emoji": emoji_json("prezent")
                        }
                    ]
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_CLIENT}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Panel Klienta"
        }
    ]

def build_client_stats_embed(member: discord.Member, total_spent: float) -> discord.Embed:
    current_role_id, needed_for_next = get_client_tier_info(total_spent)

    if current_role_id is None:
        for threshold, r_id in CLIENT_ROLE_TIERS:
            if member.guild.get_role(r_id) in member.roles:
                current_role_id = r_id
                break

    ranga_mention = f"<@&{current_role_id}>" if current_role_id else "`Brak rangi klienta`"

    if total_spent >= 1000.0:
        next_text = "`0.00 PLN (Maksymalna Ranga)`"
    else:
        next_text = f"`{needed_for_next:.2f} PLN`"

    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n        🍁 ' {SHOP_NAME} × TWOJE STATYSTYKI\n```\n"
        f"{E['strzalka']} ' **Wydałeś __u nas__:** `{total_spent:.2f} PLN`\n\n"
        f"{E['strzalka']} ' Twoja **__aktualna__** ranga: {ranga_mention}\n"
        f"{E['strzalka']} ' Do **następnej __potrzebujesz__**: {next_text}"
    )
    icon_url = member.guild.icon.url if member.guild and member.guild.icon else member.display_avatar.url
    embed.set_footer(
        text=f"© 2026 {SHOP_NAME} × Twoje Statystyki • Dziś o {datetime.now().strftime('%H:%M')}",
        icon_url=icon_url
    )
    return embed

def build_topka_embed(guild: discord.Guild, top_rows: List[Tuple[int, float]]) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)

    if not top_rows:
        opis_topki = f"> {E['info']} ' Brak zapisanych zakupów w rankingu. Bądź pierwszym klientem!"
    else:
        linie = []
        for idx, (u_id, kwota) in enumerate(top_rows, start=1):
            linie.append(f"> **{idx}.** ' <@{u_id}> {E['strzalka']} `{kwota:.2f} PLN`")
        opis_topki = "\n\n".join(linie)

    embed.description = (
        f"```\n             🍁 ' {SHOP_NAME} × TOPKA\n```\n"
        f"{opis_topki}"
    )
    icon_url = guild.icon.url if guild and guild.icon else None
    embed.set_footer(
        text=f"© 2026 {SHOP_NAME} × Topka • Dziś o {datetime.now().strftime('%H:%M')}",
        icon_url=icon_url
    )
    return embed

# --- 11.9. PANEL NASZE PRODUKTY / CENNIK (Components V2) ---
def build_products_panel_components():
    return [
        {
            "type": 10,
            "content": f"```\n              {SHOP_NAME} × NASZE PRODUKTY\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['koszyk']} ' **Masz ochotę** na film? Może wolisz __pograć w gry__? **A może szukasz** __v-bucksów__? "
                f"U nas __**znajdziesz wszystko, czego potrzebujesz**__!\n\n"
                f"> {E['strzalka']} ' **Wybierz** kategorię produktu, który Cię **interesuje**!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 3,
                    "custom_id": "pricing_main_select",
                    "placeholder": "' Wybierz Interesującą Cię Kategorię Cɛnnɪka!",
                    "options": [
                        {
                            "label": "' Nɪtro",
                            "value": "cat_nitro",
                            "emoji": emoji_json("nitro_nitro")
                        },
                        {
                            "label": "' Dɪscord",
                            "value": "cat_discord",
                            "emoji": emoji_json("3osoby")
                        },
                        {
                            "label": "' Strɛamɪngɪ",
                            "value": "cat_streamingi",
                            "emoji": emoji_json("netflix")
                        },
                        {
                            "label": "' VPNy",
                            "value": "cat_vpny",
                            "emoji": emoji_json("nordvpn")
                        },
                        {
                            "label": "' Hazard",
                            "value": "cat_hazard",
                            "emoji": emoji_json("casino_cash")
                        },
                        {
                            "label": "' Innɛ Konta",
                            "value": "cat_inne_konta",
                            "emoji": emoji_json("chatgpt")
                        },
                        {
                            "label": "' Gry",
                            "value": "cat_gry",
                            "emoji": emoji_json("gtav")
                        },
                        {
                            "label": "' Socɪal Boosty",
                            "value": "cat_social",
                            "emoji": emoji_json("instagram")
                        },
                        {
                            "label": "' Mɛtody i Dostawcy",
                            "value": "cat_metody",
                            "emoji": emoji_json("yes_box")
                        },
                        {
                            "label": "' Innɛ Usługɪ",
                            "value": "cat_inne_uslugi",
                            "emoji": emoji_json("discord_icon")
                        }
                    ]
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 12,
            "items": [{"media": {"url": BANNER_CENNIK}}]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Nasze Produkty"
        }
    ]

# ==============================================================================
# 11.10. PODKATEGORIA 1: OFERTA NITRO
# ==============================================================================
class NitroSubcategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = discord.ui.Select(
            custom_id="nitro_sub_select",
            placeholder="💡 ' Wybierz Kategorię Cɛnnɪka",
            options=[
                discord.SelectOption(
                    label="' Nɪtro Gɪft",
                    value="nitro_gift",
                    emoji=emoji_partial("nitro_nitro")
                ),
                discord.SelectOption(
                    label="' Nɪtro Trɪal",
                    value="nitro_trial",
                    emoji=emoji_partial("nitro_boost")
                ),
                discord.SelectOption(
                    label="' Nɪtro Vɪa CC",
                    value="nitro_cc",
                    emoji=emoji_partial("nitro_badge")
                ),
                discord.SelectOption(
                    label="' Sɛrvɛr Boosts",
                    value="server_boosts",
                    emoji=emoji_partial("booster")
                ),
                discord.SelectOption(
                    label="' Dɛkoracje",
                    value="dekoracje",
                    emoji=emoji_partial("discord_icon")
                ),
            ]
        )
        self.add_item(select)

def build_nitro_menu_embed() -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n        🍁 ' {SHOP_NAME} × OFERTA NITRO\n```\n"
        f"> • {E['nitro_nitro']} ' **Nɪtro Gɪft**\n"
        f"> • {E['nitro_boost']} ' **Nɪtro Trɪal**\n"
        f"> • {E['nitro_badge']} ' **Nɪtro Vɪa CC**\n"
        f"> • {E['booster']} ' **Sɛrvɛr Boosts**\n"
        f"> • {E['discord_icon']} ' **Dɛkoracje**"
    )
    embed.set_footer(text=f"© 2026 {SHOP_NAME} × Oferta Nitro • Dziś o {datetime.now().strftime('%H:%M')}")
    return embed

def build_nitro_details_embed(sub_key: str) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)

    if sub_key == "nitro_gift":
        embed.description = (
            f"### [ {E['nitro_nitro']} ] × Nɪtro Boost vɪa Gɪft 1M Bez Gwarancjɪ\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `18.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['nitro_nitro']} ] × Nɪtro Boost vɪa Gɪft 1M Z Gwarancja\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `24.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['nitro']} ] × Nɪtro Basɪc vɪa Gɪft 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `8.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['nitro_nitro']} ] × Nɪtro Boost vɪa Gɪft 1Y\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Rok`\n"
            f"> {E['pay']} ' **Cɛna:** `180.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Nɪtro Gɪft")

    elif sub_key == "nitro_trial":
        embed.description = (
            f"### [ {E['nitro_nitro']} ] × Nɪtro Boost Promolɪnk 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `10.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Nɪtro Trɪal")

    elif sub_key == "nitro_cc":
        embed.description = (
            f"### [ {E['nitro_badge']} ] × Nɪtro Boost Vɪa CC 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `20.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['nitro_badge']} ] × Nɪtro Boost Vɪa CC 1Y\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Rok`\n"
            f"> {E['pay']} ' **Cɛna:** `200.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Nɪtro Vɪa CC")

    elif sub_key == "server_boosts":
        embed.description = (
            f"### [ {E['nitro_boost']} ] × 14x Sɛrvɛr Boosts 1M Bez Gwarancjɪ\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `16.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `14 (3 Poziom)`\n\n"
            f"### [ {E['booster']} ] × 14x Sɛrvɛr Boosts 1M Z Gwarancja\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `18.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `14 (3 Poziom)`\n\n"
            f"### [ {E['booster']} ] × 28x Sɛrvɛr Boosts 1M Bez Gwarancjɪ\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `26.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `28 (3 Poziom + Dodatki)`\n\n"
            f"### [ {E['booster']} ] × 28x Sɛrvɛr Boosts 1M Z Gwarancja\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `32.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `28 (3 Poziom + Dodatki)`\n\n"
            f"### [ {E['booster']} ] × 14x Sɛrvɛr Boosts 3M Bez Gwarancjɪ\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `30.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `14 (3 Poziom)`\n\n"
            f"### [ {E['booster']} ] × 14x Sɛrvɛr Boosts 3M Z Gwarancja\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `35.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `14 (3 Poziom)`\n\n"
            f"### [ {E['booster']} ] × 28x Sɛrvɛr Boosts 3M Bez Gwarancjɪ\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `50.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `28 (3 Poziom + Dodatki)`\n\n"
            f"### [ {E['nitro_boost']} ] × 28x Sɛrvɛr Boosts 3M Z Gwarancja\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `55.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `28 (3 Poziom + Dodatki)`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Sɛrvɛr Boosts")

    elif sub_key == "dekoracje":
        progi = [
            ("20.49 PLN", "8.19 PLN"),
            ("22.49 PLN", "9.00 PLN"),
            ("29.00 PLN", "11.60 PLN"),
            ("35.00 PLN", "14.00 PLN"),
            ("37.99 PLN", "15.20 PLN"),
            ("41.99 PLN", "16.80 PLN"),
            ("48.00 PLN", "19.20 PLN"),
            ("56.99 PLN", "22.80 PLN"),
            ("66.00 PLN", "26.40 PLN"),
        ]
        linie = []
        for norm, cena in progi:
            linie.append(
                f"### [ {E['discord_icon']} ] × Dɛko vɪa Gɪft\n"
                f"> {E['pay']} ' **Normalnie:** `{norm}`\n"
                f"> {E['pay']} ' **Cɛna:** `{cena}`"
            )
        linie.append(
            f"### [ {E['discord_icon']} ] × Random Dɛko vɪa Gɪft\n"
            f"> {E['pay']} ' **Cɛna:** `9.00 PLN`"
        )
        embed.description = "\n\n".join(linie)
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Dɛcos")

    return embed

# ==============================================================================
# 11.11. PODKATEGORIA 2: OFERTA DISCORD
# ==============================================================================
class DiscordSubcategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = discord.ui.Select(
            custom_id="discord_sub_select",
            placeholder="💡 ' Wybierz Kategorię Cɛnnɪka",
            options=[
                discord.SelectOption(
                    label="' Mɛmbɛrs",
                    value="discord_members",
                    emoji=emoji_partial("3osoby")
                ),
                discord.SelectOption(
                    label="' Konta Agɛd Dɪscord",
                    value="discord_aged",
                    emoji=emoji_partial("discord_icon")
                ),
                discord.SelectOption(
                    label="' Konta Z Nɪtrɛm",
                    value="discord_nitro_acc",
                    emoji=emoji_partial("nitro_boost")
                ),
            ]
        )
        self.add_item(select)

def build_discord_menu_embed() -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n       🍁 ' {SHOP_NAME} × OFERTA DISCORD\n```\n"
        f"> • {E['3osoby']} ' **Mɛmbɛrs**\n"
        f"> • {E['discord_icon']} ' **Konta Agɛd Dɪscord**\n"
        f"> • {E['nitro_boost']} ' **Konta Z Nɪtrɛm**"
    )
    embed.set_footer(text=f"© 2026 {SHOP_NAME} × Oferta Discord • Dziś o {datetime.now().strftime('%H:%M')}")
    return embed

def build_discord_details_embed(sub_key: str) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)

    if sub_key == "discord_members":
        embed.description = (
            f"### [ {E['3osoby']} ] × Rɛal Mɛmbɛrs 1k\n"
            f"> {E['box']} ' **Ilość:** `1000`\n"
            f"> {E['pay']} ' **Cɛna:** `13.00 PLN`\n\n"
            f"### [ {E['yes_box']} ] × Onlɪnɛ Mɛmbɛrs 1k\n"
            f"> {E['box']} ' **Ilość:** `1000`\n"
            f"> {E['pay']} ' **Cɛna:** `18.00 PLN`\n\n"
            f"### [ {E['no_check']} ] × Offlɪnɛ Mɛmbɛrs 1k\n"
            f"> {E['box']} ' **Ilość:** `1000`\n"
            f"> {E['pay']} ' **Cɛna:** `10.00 PLN`\n\n"
            f"### [ {E['goat_pin']} ] × Rɛakcjɛ 1k\n"
            f"> {E['box']} ' **Ilość:** `1000`\n"
            f"> {E['pay']} ' **Cɛna:** `18.00 PLN`\n\n"
            f"{E['alert']} ' __**Dostɛpne**__ są **większe/mniejsze** ilości!"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Mɛmbɛrs")

    elif sub_key == "discord_aged":
        lata = [
            ("2024", "4.00 PLN"),
            ("2023", "5.00 PLN"),
            ("2022", "7.00 PLN"),
            ("2021", "9.00 PLN"),
            ("2020", "10.00 PLN"),
            ("2019", "14.00 PLN"),
            ("2018", "20.00 PLN"),
            ("2017", "25.00 PLN"),
            ("2016", "54.00 PLN"),
            ("2015", "230.00 PLN"),
        ]
        sekcje = []
        for rok, cena in lata:
            sekcje.append(
                f"### [ {E['discord_icon']} ] × Konto Agɛd Dɪscord {rok}\n"
                f"> {E['kalendarz']} ' **Rok Powstania:** `{rok}`\n"
                f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
                f"> {E['pay']} ' **Cɛna:** `{cena}`"
            )
        embed.description = "\n\n".join(sekcje)
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Konto Agɛd Dɪscord")

    elif sub_key == "discord_nitro_acc":
        embed.description = (
            f"### [ {E['nitro_boost']} ] × Konto Dɪscord Z Nɪtrɛm Boost 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `12.00 PLN`\n\n"
            f"### [ {E['nitro_boost']} ] × Konto Dɪscord Z Nɪtrɛm Boost 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `16.00 PLN`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Konta Z Nɪtrɛm")

    return embed

# ==============================================================================
# 11.12. PODKATEGORIA 3: OFERTA STREAMINGOWA
# ==============================================================================
class StreamingSubcategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = discord.ui.Select(
            custom_id="streaming_sub_select",
            placeholder="💡 ' Wybierz Kategorię Cɛnnɪka",
            options=[
                discord.SelectOption(
                    label="' Nɛtflɪx",
                    value="stream_netflix",
                    emoji=emoji_partial("netflix")
                ),
                discord.SelectOption(
                    label="' HboMax",
                    value="stream_hbomax",
                    emoji=emoji_partial("hbomax")
                ),
                discord.SelectOption(
                    label="' Dɪsnɛy+",
                    value="stream_disney",
                    emoji=emoji_partial("disney")
                ),
                discord.SelectOption(
                    label="' Spotɪfy Prɛmɪum",
                    value="stream_spotify",
                    emoji=emoji_partial("spotify")
                ),
                discord.SelectOption(
                    label="' Prɪmɛ Vɪdɛo",
                    value="stream_prime",
                    emoji=emoji_partial("primevideo")
                ),
                discord.SelectOption(
                    label="' Playɛr",
                    value="stream_player",
                    emoji=emoji_partial("youtube")
                ),
                discord.SelectOption(
                    label="' Cda Prɛmɪum",
                    value="stream_cda",
                    emoji=emoji_partial("youtube")
                ),
            ]
        )
        self.add_item(select)

def build_streaming_menu_embed() -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n     🍁 ' {SHOP_NAME} × OFERTA STREAMINGOWA\n```\n"
        f"> • {E['netflix']} ' **Nɛtflɪx**\n"
        f"> • {E['hbomax']} ' **HboMax**\n"
        f"> • {E['disney']} ' **Dɪsnɛy+**\n"
        f"> • {E['spotify']} ' **Spotɪfy Prɛmɪum**\n"
        f"> • {E['primevideo']} ' **Prɪmɛ Vɪdɛo**\n"
        f"> • {E['youtube']} ' **Playɛr**\n"
        f"> • {E['youtube']} ' **Cda Prɛmɪum**"
    )
    embed.set_footer(text=f"© 2026 {SHOP_NAME} × Oferta Streamingowa • Dziś o {datetime.now().strftime('%H:%M')}")
    return embed

def build_streaming_details_embed(sub_key: str) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    note = (
        f"\n\n> {E['alert']} ' **Jesteśmy** w stanie __załatwić dla Ciebie__ czas **trwania**, "
        f"jaki tylko __sobie zażyczysz__!"
    )

    if sub_key == "stream_netflix":
        embed.description = (
            f"### [ {E['netflix']} ] × Nɛtflɪx 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `8.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['netflix']} ] × Nɛtflɪx 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `10.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['netflix']} ] × Nɛtflɪx Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['pay']} ' **Cɛna:** `14.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['netflix']} ] × Nɛtflɪx Lɪfɛtɪmɛ 4K Plan FA Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `49.99 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Nɛtflɪx")

    elif sub_key == "stream_hbomax":
        embed.description = (
            f"### [ {E['hbomax']} ] × HboMax 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `5.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['hbomax']} ] × HboMax 6M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `6 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `8.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['hbomax']} ] × HboMax Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Na Zawsze`\n"
            f"> {E['pay']} ' **Cɛna:** `12.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × HboMax")

    elif sub_key == "stream_disney":
        embed.description = (
            f"### [ {E['disney']} ] × Dɪsnɛy+ Random Sub Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['pay']} ' **Cɛna:** `7.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['disney']} ] × Dɪsnɛy+ `+` Hulu Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['pay']} ' **Cɛna:** `9.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['disney']} ] × Dɪsnɛy+ `+` Hulu `+` Espn+ Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['pay']} ' **Cɛna:** `11.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Dɪsnɛy+")

    elif sub_key == "stream_spotify":
        embed.description = (
            f"### [ {E['spotify']} ] × Spotɪfy Prɛmɪum 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `9.00 PLN`\n\n"
            f"### [ {E['spotify']} ] × Spotɪfy Prɛmɪum 12M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `12 Miesięcy`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `27.00 PLN`\n\n"
            f"### [ {E['spotify']} ] × Spotɪfy Prɛmɪum Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['alert']} ' **Dostɛp:** `Kɛy Na Twoje Konto`\n"
            f"> {E['pay']} ' **Cɛna:** `30.00 PLN`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Spotɪfy Prɛmɪum")

    elif sub_key == "stream_prime":
        embed.description = (
            f"### [ {E['primevideo']} ] × Prɪmɛ Vɪdɛo 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `8.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['primevideo']} ] × Prɪmɛ Vɪdɛo 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `12.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['primevideo']} ] × Prɪmɛ Vɪdɛo 6M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `6 Miesięcy`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `15.00 PLN`\n\n"
            f"### [ {E['primevideo']} ] × Prɪmɛ Vɪdɛo Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['alert']} ' **Dostɛp:** `Full Accɛss`\n"
            f"> {E['pay']} ' **Cɛna:** `26.00 PLN`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Prɪmɛ Vɪdɛo")

    elif sub_key == "stream_player":
        embed.description = (
            f"### [ {E['youtube']} ] × Playɛr Bɛz Rɛklam 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `8.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['youtube']} ] × Playɛr Bɛz Rɛklam 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `10.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['youtube']} ] × Playɛr Bɛz Rɛklam 6M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `6 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `15.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['youtube']} ] × Playɛr Bɛz Rɛklam 12M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `12 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `18.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['youtube']} ] × Playɛr Bɛz Rɛklam Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['pay']} ' **Cɛna:** `25.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Playɛr Bɛz Rɛklam")

    elif sub_key == "stream_cda":
        embed.description = (
            f"### [ {E['youtube']} ] × Cda Prɛmɪum 1M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `8.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['youtube']} ] × Cda Prɛmɪum 3M\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `14.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`\n\n"
            f"### [ {E['youtube']} ] × Cda Prɛmɪum Lyf\n"
            f"> {E['kalendarz']} ' **Czas Trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['pay']} ' **Cɛna:** `22.00 PLN`\n"
            f"> {E['box']} ' **Ilość:** `1`"
            + note
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Cda Prɛmɪum")

    return embed

# ==============================================================================
# 11.13. PODKATEGORIA 4: OFERTA VPN
# ==============================================================================
class VpnSubcategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = discord.ui.Select(
            custom_id="vpn_sub_select",
            placeholder="📌 | Wybierz opcję.",
            options=[
                discord.SelectOption(
                    label="' NσrdVpn",
                    value="vpn_nord",
                    emoji=emoji_partial("nordvpn")
                ),
                discord.SelectOption(
                    label="' IpVanɪsh",
                    value="vpn_ipvanish",
                    emoji=emoji_partial("nordvpn")
                ),
                discord.SelectOption(
                    label="' ExprɛssVpn",
                    value="vpn_express",
                    emoji=emoji_partial("nordvpn")
                ),
            ]
        )
        self.add_item(select)

def build_vpn_menu_embed() -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n          {SHOP_NAME} × VPN\n```\n"
        f"> • {E['nordvpn']} ' **NσrdVpn**\n"
        f"> • {E['nordvpn']} ' **IpVanɪsh**\n"
        f"> • {E['nordvpn']} ' **ExprɛssVpn**"
    )
    embed.set_footer(text=f"© 2026 {SHOP_NAME} × Vpn")
    return embed

def build_vpn_details_embed(sub_key: str) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)

    if sub_key == "vpn_nord":
        embed.description = (
            f"```\n        {SHOP_NAME} × NσrdVpn\n```\n"
            f"### 「 {E['nordvpn']} 」 ' NσrdVpn 1M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `7 PLN`\n\n"
            f"### 「 {E['nordvpn']} 」 ' NσrdVpn 3M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `3 Miesiące`\n"
            f"> {E['pay']} ' **Cɛna:** `10 PLN`\n\n"
            f"### 「 {E['nordvpn']} 」 ' NσrdVpn 6M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `6 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `13 PLN`\n\n"
            f"### 「 {E['nordvpn']} 」 ' NσrdVpn 12M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `12 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `16 PLN`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × NσrdVpn")

    elif sub_key == "vpn_ipvanish":
        embed.description = (
            f"```\n        {SHOP_NAME} × IpVanɪsh\n```\n"
            f"### 「 {E['nordvpn']} 」 ' IpVanɪsh 1M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `6 PLN`\n\n"
            f"### 「 {E['nordvpn']} 」 ' IpVanɪsh 12M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `12 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `10 PLN`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × IpVanɪsh")

    elif sub_key == "vpn_express":
        embed.description = (
            f"```\n       {SHOP_NAME} × ExprɛssVpn\n```\n"
            f"### 「 {E['nordvpn']} 」 ' ExprɛssVpn 1M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `1 Miesiąc`\n"
            f"> {E['pay']} ' **Cɛna:** `4 PLN`\n\n"
            f"### 「 {E['nordvpn']} 」 ' ExprɛssVpn 12M\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `12 Miesięcy`\n"
            f"> {E['pay']} ' **Cɛna:** `7 PLN`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × ExprɛssVpn")

    return embed

# ==============================================================================
# 11.14. PODKATEGORIA 5: OFERTA HAZARD (Stakɛ)
# ==============================================================================
class HazardSubcategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = discord.ui.Select(
            custom_id="hazard_sub_select",
            placeholder="📌 | Wybierz opcję.",
            options=[
                discord.SelectOption(
                    label="' Stakɛ",
                    value="hazard_stake",
                    emoji=emoji_partial("casino_cash")
                ),
            ]
        )
        self.add_item(select)

def build_hazard_menu_embed() -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)
    embed.description = (
        f"```\n         {SHOP_NAME} × Hazard\n```\n"
        f"> • {E['casino_cash']} ' **Stakɛ**"
    )
    embed.set_footer(text=f"© 2026 {SHOP_NAME} × Hazard")
    return embed

def build_hazard_details_embed(sub_key: str) -> discord.Embed:
    embed = discord.Embed(color=THEME_COLOR)

    if sub_key == "hazard_stake":
        embed.description = (
            f"```\n         {SHOP_NAME} × Stakɛ\n```\n"
            f"### 「 {E['casino_cash']} 」 ' Stakɛ LvL 2\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['klient_500']} ' **Poziom Konta:** `2 LvL`\n"
            f"> {E['weryfikacja']} ' **Dσstɛp:** `Full Access`\n"
            f"> {E['pay']} ' **Cɛna:** `4 PLN`\n\n"
            f"### 「 {E['casino_cash']} 」 ' Stakɛ LvL 2\n"
            f"> {E['kalendarz']} ' **Czas trwania:** `Lɪfɛtɪmɛ`\n"
            f"> {E['klient_500']} ' **Poziom Konta:** `2 LvL`\n"
            f"> {E['weryfikacja']} ' **Dσstɛp:** `Na Twój Email`\n"
            f"> {E['pay']} ' **Cɛna:** `8 PLN`"
        )
        embed.set_footer(text=f"© 2026 {SHOP_NAME} × Stakɛ")

    return embed

# --- 11.15. WIADOMOŚĆ WEWNĄTRZ NOWO OTWARTEGO TICKETA ZAKUPOWEGO / POMOCY ---
def build_opened_ticket_components(
    user: discord.Member,
    produkt: str,
    ilosc: str,
    platnosc: str,
    kod: str,
    kod_reklamacji: str
):
    return [
        {
            "type": 10,
            "content": f"```\n              {SHOP_NAME} × TICKET ZAKUPOWY\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 9,
            "components": [
                {
                    "type": 10,
                    "content": (
                        f"> {E['osoba']} ' **Klient:** {user.mention} (`{user.id}`)\n"
                        f"> {E['box']} ' **Produkt:** `{produkt}`\n"
                        f"> {E['koszyk']} ' **Ilość sztuk:** `{ilosc}`\n"
                        f"> {E['portfel']} ' **Metoda płatności:** `{platnosc}`\n"
                        f"> {E['prezent']} ' **Kod zniżkowy:** `{kod if kod else 'Brak'}`\n"
                        f"> {E['hasztag']} ' **Kod Reklamacji:** `{kod_reklamacji}`"
                    )
                }
            ],
            "accessory": {
                "type": 11,
                "media": {"url": user.display_avatar.replace(format="png", size=256).url}
            }
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"{E['info']} ' **Administracja** wkrótce zajmie się Twoim zamówieniem!\n"
                f"{E['lupa']} ' Po otrzymaniu produktu wystaw **+rep** na kanale <#{LEGIT_CHECK_CHANNEL_ID}>, "
                f"a Twój ticket **zamknie się automatycznie**, a kwota doliczy się do Twoich statystyk!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 3,
                    "custom_id": "ticket_claim_btn",
                    "label": "' Przejmij Ticket",
                    "emoji": emoji_json("yes_box")
                },
                {
                    "type": 2,
                    "style": 4,
                    "custom_id": "ticket_close_btn",
                    "label": "' Zamknij Ticket",
                    "emoji": emoji_json("x")
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Obsługa Klienta"
        }
    ]

# --- 11.16. WIADOMOŚĆ WEWNĄTRZ TICKETA REKLAMACYJNEGO ---
def build_complaint_ticket_components(
    user: discord.Member,
    kod_rek: str,
    data_zam: str,
    produkt: str,
    sprzedawca_id: str,
    attachment_urls: list
):
    sprzedawca_mention = f"<@{sprzedawca_id}>" if sprzedawca_id.isdigit() else sprzedawca_id
    components = [
        {
            "type": 10,
            "content": f"```\n              {SHOP_NAME} × TICKET REKLAMACJI\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 9,
            "components": [
                {
                    "type": 10,
                    "content": (
                        f"> {E['osoba']} ' **Klient:** {user.mention} (`{user.id}`)\n"
                        f"> {E['hasztag']} ' **Kod Reklamacji:** `{kod_rek}`\n"
                        f"> {E['kalendarz']} ' **Data Zamknięcia Ticketa:** `{data_zam}`\n"
                        f"> {E['box']} ' **Zakupiony Produkt:** `{produkt}`\n"
                        f"> {E['seller']} ' **Sprzedawca:** {sprzedawca_mention}"
                    )
                }
            ],
            "accessory": {
                "type": 11,
                "media": {"url": user.display_avatar.replace(format="png", size=256).url}
            }
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"{E['reklamacje']} ' **Zgłoszenie reklamacyjne** zostało utworzone. "
                f"Sprzedawca {sprzedawca_mention} wkrótce zweryfikuje Twoje zgłoszenie!"
            )
        },
    ]

    if attachment_urls:
        components.append({"type": 14, "divider": True, "spacing": 1})
        components.append({
            "type": 12,
            "items": [{"media": {"url": url}} for url in attachment_urls[:2]]
        })

    components.extend([
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 3,
                    "custom_id": "ticket_claim_btn",
                    "label": "' Przejmij Reklamację",
                    "emoji": emoji_json("yes_box")
                },
                {
                    "type": 2,
                    "style": 4,
                    "custom_id": "ticket_close_btn",
                    "label": "' Zamknij Ticket",
                    "emoji": emoji_json("x")
                }
            ]
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['reklamacje']} © 2026 {SHOP_NAME} × Dział Reklamacji"
        }
    ])
    return components

# ==============================================================================
# 12. FORMULARZE (MODALE): ZAKUP, REKLAMACJA, WYSZUKAJ PRODUKT, WYSTAW OPINIĘ
# ==============================================================================
async def open_purchase_modal(bot: commands.Bot, interaction: discord.Interaction):
    modal_payload = {
        "type": 9,
        "data": {
            "custom_id": "modal_zakup_submit",
            "title": "Formularz Zakupu",
            "components": [
                {
                    "type": 18,
                    "label": "Jaki produkt chcesz zakupić?",
                    "component": {
                        "type": 4,
                        "custom_id": "produkt",
                        "style": 1,
                        "placeholder": "np. Konto Spotify Premium",
                        "required": True
                    }
                },
                {
                    "type": 18,
                    "label": "Ile sztuk chcesz zakupić?",
                    "component": {
                        "type": 4,
                        "custom_id": "ilosc",
                        "style": 1,
                        "placeholder": "np. 1",
                        "required": True
                    }
                },
                {
                    "type": 18,
                    "label": "Jakiej Metody Płatności Użyjesz?",
                    "component": {
                        "type": 3,
                        "custom_id": "platnosc",
                        "placeholder": "Wybierz metodę płatności",
                        "min_values": 1,
                        "max_values": 1,
                        "required": True,
                        "options": get_payment_options()
                    }
                },
                {
                    "type": 18,
                    "label": "Kod Zniżkowy",
                    "component": {
                        "type": 4,
                        "custom_id": "kod_znizkowy",
                        "style": 1,
                        "placeholder": "Wpisz kod zniżkowy (jeśli posiadasz)",
                        "required": False
                    }
                }
            ]
        }
    }
    await bot.http.request(
        Route(
            'POST',
            '/interactions/{interaction_id}/{interaction_token}/callback',
            interaction_id=interaction.id,
            interaction_token=interaction.token
        ),
        json=modal_payload
    )

async def open_complaint_modal(bot: commands.Bot, interaction: discord.Interaction):
    base_components = [
        {
            "type": 18,
            "label": "Kod Rɛklamacji",
            "component": {
                "type": 4,
                "custom_id": "kod_reklamacji",
                "style": 1,
                "placeholder": "Np. ABC123DEF4",
                "required": True
            }
        },
        {
            "type": 18,
            "label": "Data Zamknięcia Tickɛta Zamowɪɛnɪa",
            "component": {
                "type": 4,
                "custom_id": "data_zamkniecia",
                "style": 1,
                "placeholder": "Np. 31.12.2025",
                "required": True
            }
        },
        {
            "type": 18,
            "label": "Zakupɪony Produkt",
            "component": {
                "type": 4,
                "custom_id": "zakupiony_produkt",
                "style": 2,
                "placeholder": "Np. Dɪsnɛy+ Lɪfɛtɪmɛ",
                "required": True
            }
        },
        {
            "type": 18,
            "label": "Sprzɛdawca",
            "component": {
                "type": 5,
                "custom_id": "sprzedawca",
                "placeholder": "Wybierz sprzedawcę...",
                "min_values": 1,
                "max_values": 1,
                "required": True
            }
        },
        {
            "type": 18,
            "label": "Scrɛɛnshoty (lɛgɪtka + płatność)",
            "component": {
                "type": 19,
                "custom_id": "screenshoty",
                "min_values": 0,
                "max_values": 2,
                "required": False
            }
        }
    ]

    modal_payload = {
        "type": 9,
        "data": {
            "custom_id": "modal_reklamacja_submit",
            "title": "Formularz Dotyczący Rɛklamacji",
            "components": base_components
        }
    }

    try:
        await bot.http.request(
            Route(
                'POST',
                '/interactions/{interaction_id}/{interaction_token}/callback',
                interaction_id=interaction.id,
                interaction_token=interaction.token
            ),
            json=modal_payload
        )
    except discord.HTTPException:
        modal_payload["data"]["components"][4] = {
            "type": 18,
            "label": "Scrɛɛnshoty (lɛgɪtka + płatność)",
            "component": {
                "type": 4,
                "custom_id": "screenshoty",
                "style": 1,
                "placeholder": "Wklej link do screenów lub wyślij je po otwarciu ticketa",
                "required": False
            }
        }
        await bot.http.request(
            Route(
                'POST',
                '/interactions/{interaction_id}/{interaction_token}/callback',
                interaction_id=interaction.id,
                interaction_token=interaction.token
            ),
            json=modal_payload
        )

async def open_search_product_modal(bot: commands.Bot, interaction: discord.Interaction):
    modal_payload = {
        "type": 9,
        "data": {
            "custom_id": "modal_search_product_submit",
            "title": "Wyszukaj Produkt",
            "components": [
                {
                    "type": 18,
                    "label": "Nazwa Produktu",
                    "component": {
                        "type": 4,
                        "custom_id": "szukana_nazwa",
                        "style": 1,
                        "placeholder": "np. nitro, netflix, spotify, aged, stake...",
                        "required": True
                    }
                }
            ]
        }
    }
    await bot.http.request(
        Route(
            'POST',
            '/interactions/{interaction_id}/{interaction_token}/callback',
            interaction_id=interaction.id,
            interaction_token=interaction.token
        ),
        json=modal_payload
    )

async def open_review_modal(bot: commands.Bot, interaction: discord.Interaction):
    star_opts = get_star_rating_options()
    modal_payload = {
        "type": 9,
        "data": {
            "custom_id": "modal_review_submit",
            "title": "Wystaw opinię",
            "components": [
                {
                    "type": 18,
                    "label": "Treść opinii",
                    "component": {
                        "type": 4,
                        "custom_id": "tresc_opinii",
                        "style": 2,
                        "placeholder": "Napisz Treść Swojej Opinii!",
                        "required": True
                    }
                },
                {
                    "type": 18,
                    "label": "Co możemy poprawić?",
                    "component": {
                        "type": 4,
                        "custom_id": "co_poprawic",
                        "style": 1,
                        "placeholder": "Co możemy poprawić?",
                        "required": False
                    }
                },
                {
                    "type": 18,
                    "label": "Jakość Produktow",
                    "component": {
                        "type": 3,
                        "custom_id": "ocena_jakosc",
                        "placeholder": "⭐ ' Wybierz Subiektywną Ocenę!",
                        "min_values": 1,
                        "max_values": 1,
                        "required": True,
                        "options": star_opts
                    }
                },
                {
                    "type": 18,
                    "label": "Czas Realizacji",
                    "component": {
                        "type": 3,
                        "custom_id": "ocena_czas",
                        "placeholder": "⭐ ' Wybierz Subiektywną Ocenę!",
                        "min_values": 1,
                        "max_values": 1,
                        "required": True,
                        "options": star_opts
                    }
                },
                {
                    "type": 18,
                    "label": "Przebieg Transakcjɪ",
                    "component": {
                        "type": 3,
                        "custom_id": "ocena_przebieg",
                        "placeholder": "⭐ ' Wybierz Subiektywną Ocenę!",
                        "min_values": 1,
                        "max_values": 1,
                        "required": True,
                        "options": star_opts
                    }
                }
            ]
        }
    }
    await bot.http.request(
        Route(
            'POST',
            '/interactions/{interaction_id}/{interaction_token}/callback',
            interaction_id=interaction.id,
            interaction_token=interaction.token
        ),
        json=modal_payload
    )

def extract_modal_values(data: dict) -> tuple[dict, list]:
    results = {}
    attachment_urls = []
    resolved_attachments = data.get("resolved", {}).get("attachments", {})

    for row in data.get("components", []):
        comp = row.get("component")
        if comp:
            cid = comp.get("custom_id")
            if "values" in comp and comp["values"]:
                vals = comp["values"]
                if cid == "screenshoty":
                    for att_id in vals:
                        att_obj = resolved_attachments.get(str(att_id), {})
                        if "url" in att_obj:
                            attachment_urls.append(att_obj["url"])
                else:
                    results[cid] = vals[0]
            else:
                results[cid] = comp.get("value", "")

        for sub in row.get("components", []):
            cid = sub.get("custom_id")
            if "values" in sub and sub["values"]:
                results[cid] = sub["values"][0]
            else:
                results[cid] = sub.get("value", "")

    return results, attachment_urls

def normalize_search_text(txt: str) -> str:
    replacements = {
        "ɪ": "i", "ɛ": "e", "σ": "o", "ł": "l", "ą": "a", "ę": "e",
        "ś": "s", "ć": "c", "ń": "n", "ó": "o", "ź": "z", "ż": "z"
    }
    res = txt.lower()
    for k, v in replacements.items():
        res = res.replace(k, v)
    return res

# ==============================================================================
# 13. KLASA GŁÓWNA BOTA + NATYCHMIASTOWA SYNCHRONIZACJA KOMEND NA SERWERZE
# ==============================================================================
class HexullyShopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="!", intents=intents)
        self._emojis_synced = False
        self._commands_synced = False
        self._last_daily_lc_date = datetime.now().strftime("%d.%m.%Y")

    async def sync_application_emojis(self):
        if self._emojis_synced:
            return
        try:
            data = await self.http.request(
                Route('GET', '/applications/{application_id}/emojis', application_id=self.application_id)
            )
            items = data.get("items", []) if isinstance(data, dict) else []
            by_id = {str(item["id"]): item for item in items}
            by_name = {item["name"].lower(): item for item in items}

            updated_count = 0
            for key, info in RAW_EMOJIS.items():
                matched = by_id.get(str(info["id"])) or by_name.get(info["name"].lower())
                if matched:
                    info["id"] = str(matched["id"])
                    info["name"] = matched["name"]
                    info["animated"] = bool(matched.get("animated", False))
                    updated_count += 1

            rebuild_emoji_strings()
            self._emojis_synced = True
            print(f"✅ Zsynchronizowano {updated_count} emotek z Discord Developer Portal!")
        except Exception as e:
            print(f"⚠️ Pominięto synchronizację emotek przy starcie: {e}")

    async def sync_all_commands_to_guilds(self):
        if self._commands_synced:
            return
        try:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"✅ Natychmiast zsynchronizowano {len(synced)} komend (/) dla serwera: {guild.name}")
            self._commands_synced = True
        except Exception as e:
            print(f"⚠️ Błąd auto-synchronizacji komend: {e}")

    @tasks.loop(minutes=6)
    async def background_stats_loop(self):
        await self.wait_until_ready()
        today_str = datetime.now().strftime("%d.%m.%Y")
        if today_str != self._last_daily_lc_date:
            self._last_daily_lc_date = today_str
            await update_or_send_daily_lc_message(self)

        for guild in self.guilds:
            await update_all_live_channels(self, guild, force=False)

    async def on_ready(self):
        await self.sync_application_emojis()
        await self.sync_all_commands_to_guilds()
        if not self.background_stats_loop.is_running():
            self.background_stats_loop.start()
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=SHOP_NAME)
        )
        print(f"⭐ {self.user} ({SHOP_NAME}) JEST ONLINE I GOTOWY DO PRACY!")
        for guild in self.guilds:
            asyncio.create_task(update_all_live_channels(self, guild, force=False))

bot = HexullyShopBot()

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def cmd_sync_tree(ctx: commands.Context):
    msg = await ctx.send("⏳ Synchronizowanie komend `/` bezpośrednio z tym serwerem...")
    try:
        await bot.sync_application_emojis()
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await msg.edit(content=f"{E['yes_box']} Natychmiast zsynchronizowano **{len(synced)}** komend `/` na tym serwerze!")
    except Exception as e:
        await msg.edit(content=f"❌ Błąd podczas synchronizacji: `{e}`")

# ==============================================================================
# 14. ZDARZENIA: WEJŚCIE/WYJŚCIE, REAKCJE, +REP (NALICZANIE KLIENTA I SPRZEDAWCY)
# ==============================================================================
@bot.event
async def on_member_join(member: discord.Member):
    if WELCOME_CHANNEL_ID != 123456789012345678:
        try:
            await send_v2_container(bot, WELCOME_CHANNEL_ID, build_welcome_components(member, member.guild))
        except Exception as e:
            print(f"Błąd wysyłania powitania: {e}")

    ch_members = member.guild.get_channel(VC_CZLONKOWIE_ID)
    await safe_rename_channel(ch_members, f"👤〢członków➔{member.guild.member_count}", force=False)

@bot.event
async def on_member_remove(member: discord.Member):
    ch_members = member.guild.get_channel(VC_CZLONKOWIE_ID)
    await safe_rename_channel(ch_members, f"👤〢członków➔{member.guild.member_count}", force=False)

async def handle_czy_legit_reaction_change(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return
    legit_msg_id = int(db_get_setting("czy_legit_msg_id", "0") or "0")

    if not legit_msg_id or payload.message_id != legit_msg_id:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        msg = await channel.fetch_message(legit_msg_id)
        yes_id = int(RAW_EMOJIS["yes_box"]["id"])
        positive_votes = 0
        for react in msg.reactions:
            if getattr(react.emoji, "id", None) == yes_id or str(react.emoji) == "✅":
                positive_votes = max(0, react.count - 1)
                break

        db_set_setting("total_czy_legit_count", str(positive_votes))
        await safe_rename_channel(channel, f"💜・czy・jesteśmy・legit➔{positive_votes}", force=False)
    except Exception as e:
        print(f"Błąd aktualizacji licznika Czy Jesteśmy Legit: {e}")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await handle_czy_legit_reaction_change(payload)

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    await handle_czy_legit_reaction_change(payload)

@bot.event
async def on_message(message: discord.Message):
    global LAST_LC_STICKY_MESSAGE_ID
    if message.author.bot or not message.guild:
        return

    # 1. Zapisywanie wiadomości do pamięci transkryptu, jeśli to kanał ticketa
    if message.channel.id in TICKET_TRANSCRIPTS:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_line = f"[{timestamp}] {message.author} ({message.author.id}): {message.content}"
        if message.attachments:
            for att in message.attachments:
                msg_line += f" [Załącznik: {att.url}]"
        TICKET_TRANSCRIPTS[message.channel.id].append(msg_line)

    # 2. Obsługa +rep wyłącznie na kanale LEGIT_CHECK_CHANNEL_ID (1539238571083436052)
    if message.channel.id == LEGIT_CHECK_CHANNEL_ID:
        if message.content.strip().lower().startswith("+rep"):
            try:
                await message.add_reaction(emoji_partial("yes_box"))
                await message.add_reaction(emoji_partial("serce"))
            except Exception:
                pass

            # Odświeżenie dolnego panelu Sticky Legit Check
            sticky_id_str = db_get_setting("lc_sticky_msg_id", "")
            if LAST_LC_STICKY_MESSAGE_ID is None and sticky_id_str.isdigit():
                LAST_LC_STICKY_MESSAGE_ID = int(sticky_id_str)

            if LAST_LC_STICKY_MESSAGE_ID:
                try:
                    old_msg = await message.channel.fetch_message(LAST_LC_STICKY_MESSAGE_ID)
                    await old_msg.delete()
                except Exception:
                    pass
            else:
                try:
                    async for msg in message.channel.history(limit=10):
                        if msg.author.id == bot.user.id:
                            await msg.delete()
                            break
                except Exception:
                    pass

            try:
                res = await send_v2_container(bot, message.channel.id, build_legit_check_components())
                if isinstance(res, dict) and "id" in res:
                    LAST_LC_STICKY_MESSAGE_ID = int(res["id"])
                    db_set_setting("lc_sticky_msg_id", str(LAST_LC_STICKY_MESSAGE_ID))
            except Exception as e:
                print(f"Błąd wysyłania sticky LC: {e}")

            # Szukamy aktywnego ticketa klienta
            ticket_channel = None
            if message.author.id in ACTIVE_TICKETS:
                ticket_channel = message.guild.get_channel(ACTIVE_TICKETS[message.author.id])

            if not ticket_channel:
                for ch in message.guild.text_channels:
                    if ch.topic and f"ticket_owner:{message.author.id}" in ch.topic:
                        ticket_channel = ch
                        break

            # Pobranie zamówienia z pending_orders (jeśli użyto /zrealizowano)
            pending_info = db_pop_pending_order(message.author.id)
            spent_amount = pending_info["amount"] if pending_info else 0.0
            seller_already_settled = pending_info["seller_settled"] if pending_info else False
            seller_id_from_order = pending_info["seller_id"] if pending_info else None

            if not spent_amount or spent_amount <= 0:
                if ticket_channel and ticket_channel.id in TICKET_METADATA:
                    meta_kwota = TICKET_METADATA[ticket_channel.id].get("kwota", "")
                    spent_amount = parse_amount_from_text(meta_kwota)
                if not spent_amount or spent_amount <= 0:
                    spent_amount = parse_amount_from_text(message.content)

            spent_amount = max(0.0, float(spent_amount or 0.0))

            # Jeśli zamówienie NIE było jeszcze doliczone sprzedawcy przez /zrealizowano,
            # doliczamy je do jego tygodniowych zarobków na podstawie oznaczenia @seller w +rep!
            if not seller_already_settled and spent_amount > 0:
                target_seller_id = seller_id_from_order
                if not target_seller_id and message.mentions:
                    for mentioned in message.mentions:
                        if not mentioned.bot and mentioned.id != message.author.id:
                            target_seller_id = mentioned.id
                            break
                if not target_seller_id and ticket_channel and ticket_channel.id in TICKET_METADATA:
                    target_seller_id = TICKET_METADATA[ticket_channel.id].get("claimed_by")

                if target_seller_id:
                    db_add_seller_sale(target_seller_id, spent_amount)

            # Aktualizacja statystyk klienta, rang, licznika LC oraz Dziennego LC
            new_total_spent = db_add_client_spent(message.author.id, spent_amount)
            assigned_role_id = await sync_member_client_roles(message.author, new_total_spent)
            db_increment_setting("total_lc_count", 1)

            daily_summary = db_record_daily_lc(spent_amount)
            asyncio.create_task(update_or_send_daily_lc_message(bot, daily_summary))
            asyncio.create_task(update_all_live_channels(bot, message.guild, force=False))

            # Zamknięcie ticketa i wysłanie podsumowania na DM
            if ticket_channel:
                meta = TICKET_METADATA.get(ticket_channel.id, {})
                kod_reklamacji = meta.get("kod_reklamacji")
                if not kod_reklamacji and ticket_channel.topic and "kod:" in ticket_channel.topic:
                    kod_reklamacji = ticket_channel.topic.split("kod:")[-1].strip()
                if not kod_reklamacji:
                    kod_reklamacji = generuj_kod_reklamacji()

                data_dzis = datetime.now().strftime("%d.%m.%Y")
                ranga_dm_info = f"<@&{assigned_role_id}>" if assigned_role_id else "Klient"

                try:
                    await message.author.send(
                        f"{E['yes_box']} **Dziękujemy za wystawienie opinii (+rep) w {SHOP_NAME}!**\n"
                        f"> {E['pay']} **Doliczono do statystyk:** `+{spent_amount:.2f} PLN` (Łącznie wydałeś: `{new_total_spent:.2f} PLN`)\n"
                        f"> {E['klient_500']} **Twoja aktualna ranga:** {ranga_dm_info}\n"
                        f"> {E['hasztag']} **Twój Kod Reklamacji:** `{kod_reklamacji}`\n"
                        f"> {E['kalendarz']} **Data zamknięcia ticketa:** `{data_dzis}`\n"
                        f"-# Zachowaj te dane na wypadek składania reklamacji!"
                    )
                except Exception:
                    pass

                try:
                    await send_v2_container(
                        bot,
                        ticket_channel.id,
                        [
                            {
                                "type": 10,
                                "content": f"```\n              {SHOP_NAME} × ZAMYKANIE TICKETA\n```"
                            },
                            {"type": 14, "divider": True, "spacing": 1},
                            {
                                "type": 10,
                                "content": (
                                    f"> {E['yes_box']} ' Klient {message.author.mention} wystawił **+rep** na kanale <#{LEGIT_CHECK_CHANNEL_ID}>!\n"
                                    f"> {E['pay']} ' **Zaktualizowano wydatki klienta:** `{new_total_spent:.2f} PLN`\n"
                                    f"> {E['hasztag']} ' **Kod Reklamacji:** `{kod_reklamacji}` (`{data_dzis}`)\n"
                                    f"> {E['info']} ' Ticket zostanie **automatycznie zamknięty i zapisany w logach** za **5 sekund**..."
                                )
                            }
                        ]
                    )
                    await asyncio.sleep(5)
                    await close_ticket_with_transcript(
                        bot,
                        ticket_channel,
                        message.author,
                        reason=f"Automatyczne zamknięcie po wystawieniu +rep (+{spent_amount:.2f} PLN)"
                    )
                except Exception as e:
                    print(f"Błąd podczas auto-zamykania ticketa: {e}")

    await bot.process_commands(message)

# ==============================================================================
# 15. OBSŁUGA INTERAKCJI (ROZLICZENIA, CENNIK, TICKETY, WYSZUKIWARKA, OPINIE)
# ==============================================================================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        cid = interaction.data.get("custom_id")
        values = interaction.data.get("values", [])

        # 1. Przycisk "Moje Statystyki" w Panelu Rozliczeniowym Sprzedawców
        if cid == "seller_my_settlement_btn":
            stats = db_get_seller_settlement(interaction.user.id)
            embed = build_seller_individual_settlement_embed(interaction.user, stats)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # 2. Przycisk Wyszukiwania Produktu
        elif cid == "search_product_btn":
            try:
                await open_search_product_modal(bot, interaction)
            except Exception as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Błąd otwierania wyszukiwarki: `{e}`", ephemeral=True)

        # 3. Przycisk Wystawiania Opinii
        elif cid == "open_review_modal_btn":
            try:
                await open_review_modal(bot, interaction)
            except Exception as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Błąd otwierania formularza opinii: `{e}`", ephemeral=True)

        # 4. Główne menu cennika (/panel_produkty)
        elif cid == "pricing_main_select" and values:
            wybor = values[0]
            if wybor == "cat_nitro":
                await interaction.response.send_message(
                    embed=build_nitro_menu_embed(),
                    view=NitroSubcategoryView(),
                    ephemeral=True
                )
            elif wybor == "cat_discord":
                await interaction.response.send_message(
                    embed=build_discord_menu_embed(),
                    view=DiscordSubcategoryView(),
                    ephemeral=True
                )
            elif wybor == "cat_streamingi":
                await interaction.response.send_message(
                    embed=build_streaming_menu_embed(),
                    view=StreamingSubcategoryView(),
                    ephemeral=True
                )
            elif wybor == "cat_vpny":
                await interaction.response.send_message(
                    embed=build_vpn_menu_embed(),
                    view=VpnSubcategoryView(),
                    ephemeral=True
                )
            elif wybor == "cat_hazard":
                await interaction.response.send_message(
                    embed=build_hazard_menu_embed(),
                    view=HazardSubcategoryView(),
                    ephemeral=True
                )
            else:
                nazwy_kategorii = {
                    "cat_inne_konta": "Innɛ Konta",
                    "cat_gry": "Gry",
                    "cat_social": "Socɪal Boosty",
                    "cat_metody": "Mɛtody i Dostawcy",
                    "cat_inne_uslugi": "Innɛ Usługɪ",
                }
                nazwa = nazwy_kategorii.get(wybor, wybor)
                embed = discord.Embed(
                    color=THEME_COLOR,
                    description=(
                        f"```\n        🍁 ' {SHOP_NAME} × OFERTA {nazwa.upper()}\n```\n"
                        f"> {E['info']} ' Oferta z kategorii **{nazwa}** jest aktualnie przygotowywana!"
                    )
                )
                embed.set_footer(text=f"© 2026 {SHOP_NAME} × Oferta {nazwa}")
                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif cid == "nitro_sub_select" and values:
            await interaction.response.send_message(
                embed=build_nitro_details_embed(values[0]),
                ephemeral=True
            )

        elif cid == "discord_sub_select" and values:
            await interaction.response.send_message(
                embed=build_discord_details_embed(values[0]),
                ephemeral=True
            )

        elif cid == "streaming_sub_select" and values:
            await interaction.response.send_message(
                embed=build_streaming_details_embed(values[0]),
                ephemeral=True
            )

        elif cid == "vpn_sub_select" and values:
            await interaction.response.send_message(
                embed=build_vpn_details_embed(values[0]),
                ephemeral=True
            )

        elif cid == "hazard_sub_select" and values:
            await interaction.response.send_message(
                embed=build_hazard_details_embed(values[0]),
                ephemeral=True
            )

        # 5. Wybór kategorii w panelu ticketów (/panel_tickety)
        elif cid == "ticket_category_select" and values:
            wybor = values[0]
            if wybor == "zakup":
                try:
                    await open_purchase_modal(bot, interaction)
                except Exception as e:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"❌ Błąd formularza zakupu: `{e}`", ephemeral=True)
            elif wybor == "reklamacja":
                try:
                    await open_complaint_modal(bot, interaction)
                except Exception as e:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"❌ Błąd formularza reklamacji: `{e}`", ephemeral=True)
            else:
                await interaction.response.defer(ephemeral=True)
                guild = interaction.guild
                kod_rek = generuj_kod_reklamacji()
                category = guild.get_channel(CATEGORY_POMOC_ID)

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True,
                        read_message_history=True
                    )
                }

                channel = await guild.create_text_channel(
                    name=f"🎫・{wybor}-{interaction.user.name[:12]}",
                    category=category,
                    topic=f"ticket_owner:{interaction.user.id}|kod:{kod_rek}",
                    overwrites=overwrites
                )

                ACTIVE_TICKETS[interaction.user.id] = channel.id
                TICKET_TRANSCRIPTS[channel.id] = [
                    f"--- Otwarto ticket ({wybor.upper()}) przez {interaction.user} ({interaction.user.id}) ---"
                ]
                TICKET_METADATA[channel.id] = {
                    "owner_id": interaction.user.id,
                    "typ": wybor,
                    "produkt": f"Zgłoszenie: {wybor.upper()}",
                    "ilosc": "1",
                    "platnosc": "-",
                    "kod": "Brak",
                    "kod_reklamacji": kod_rek,
                    "claimed_by": None,
                    "kwota": "-"
                }

                await send_v2_container(
                    bot,
                    channel.id,
                    build_opened_ticket_components(
                        interaction.user,
                        f"Kategoria: {wybor.upper()}",
                        "-",
                        "-",
                        "Brak",
                        kod_rek
                    )
                )
                await interaction.followup.send(
                    f"{E['yes_box']} Twój ticket został otwarty: {channel.mention}",
                    ephemeral=True
                )

        elif cid == "ticket_claim_btn":
            if not interaction.user.guild_permissions.manage_messages:
                return await interaction.response.send_message(
                    f"{E['x']} Tylko administracja oraz sprzedawcy mogą przejąć ticket!",
                    ephemeral=True
                )

            if interaction.channel_id in TICKET_METADATA:
                TICKET_METADATA[interaction.channel_id]["claimed_by"] = interaction.user.id

            await interaction.response.defer()
            await send_v2_container(
                bot,
                interaction.channel_id,
                [
                    {
                        "type": 10,
                        "content": (
                            f"> {E['yes_box']} ' Ticket został przejęty przez sprzedawcę {interaction.user.mention}!"
                        )
                    }
                ]
            )

        elif cid == "ticket_close_btn":
            await interaction.response.send_message(
                f"{E['info']} Zamykanie ticketa i generowanie transkryptu za **3 sekundy**..."
            )
            await asyncio.sleep(3)
            await close_ticket_with_transcript(
                bot,
                interaction.channel,
                interaction.user,
                reason=f"Zamknięty ręcznie przez {interaction.user}"
            )

        # 6. Panel Klienta (Statystyki / Topka / Zniżka)
        elif cid == "client_panel_select" and values:
            wybor = values[0]
            if wybor == "statystyki":
                total_spent = db_get_client_spent(interaction.user.id)
                if total_spent > 0 and isinstance(interaction.user, discord.Member):
                    await sync_member_client_roles(interaction.user, total_spent)
                embed = build_client_stats_embed(interaction.user, total_spent)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif wybor == "topka":
                top_rows = db_get_top_clients(limit=10)
                embed = build_topka_embed(interaction.guild, top_rows)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif wybor == "znizka":
                embed = discord.Embed(
                    color=THEME_COLOR,
                    description=(
                        f"```\n        🍁 ' {SHOP_NAME} × WYLOSUJ ZNIŻKĘ\n```\n"
                        f"> {E['prezent']} ' System losowania kodów rabatowych jest gotowy do podpięcia!"
                    )
                )
                embed.set_footer(text=f"© 2026 {SHOP_NAME} × Zniżki Klientów")
                await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------------------------
    # B. WYSŁANIE FORMULARZY (ZAKUP, REKLAMACJA, WYSZUKAJ PRODUKT, WYSTAW OPINIĘ)
    # --------------------------------------------------------------------------
    elif interaction.type == discord.InteractionType.modal_submit:
        cid = interaction.data.get("custom_id")

        if cid == "modal_search_product_submit":
            await interaction.response.defer(ephemeral=True)
            fields, _ = extract_modal_values(interaction.data)
            query_raw = fields.get("szukana_nazwa", "").strip()
            query_norm = normalize_search_text(query_raw)

            matches = [
                p for p in PRODUCT_CATALOG
                if query_norm in normalize_search_text(p["name"])
            ]

            embed = discord.Embed(color=THEME_COLOR)
            if not matches:
                embed.description = (
                    f"```\n       {SHOP_NAME} × WYNIKI WYSZUKIWANIA\n```\n"
                    f"> {E['x']} ' Nie znaleziono produktu pasującego do frazy: **`{query_raw}`**.\n"
                    f"> {E['info']} ' Spróbuj wpisać krótszą nazwę, np. `nitro`, `netflix`, `spotify`, `aged`, `vpn`, `stake`."
                )
            else:
                lines = [
                    f"> • {E['koszyk']} **{item['name']}** {E['strzalka']} `{item['price']}`"
                    for item in matches[:25]
                ]
                embed.description = (
                    f"```\n       {SHOP_NAME} × WYNIKI WYSZUKIWANIA\n```\n"
                    f"{E['lupa']} ' Znalezione produkty dla frazy **`{query_raw}`** ({len(matches)}):\n\n"
                    + "\n".join(lines)
                )
            embed.set_footer(text=f"© 2026 {SHOP_NAME} × Wyszukiwanie Produktów")
            await interaction.followup.send(embed=embed, ephemeral=True)

        elif cid == "modal_review_submit":
            await interaction.response.defer(ephemeral=True)
            fields, _ = extract_modal_values(interaction.data)
            tresc = fields.get("tresc_opinii", "Polecam!").strip()
            poprawic = fields.get("co_poprawic", "nic").strip() or "nic"

            try:
                jakosc = int(fields.get("ocena_jakosc", "5"))
            except ValueError:
                jakosc = 5
            try:
                czas = int(fields.get("ocena_czas", "5"))
            except ValueError:
                czas = 5
            try:
                przebieg = int(fields.get("ocena_przebieg", "5"))
            except ValueError:
                przebieg = 5

            channel = interaction.channel

            old_sticky_id = int(db_get_setting("opinie_sticky_msg_id", "0") or "0")
            if old_sticky_id and channel:
                try:
                    old_sticky_msg = await channel.fetch_message(old_sticky_id)
                    await old_sticky_msg.delete()
                except Exception:
                    pass

            review_res = await send_v2_container(
                bot,
                interaction.channel_id,
                build_published_review_components(
                    interaction.user,
                    tresc,
                    poprawic,
                    jakosc,
                    czas,
                    przebieg
                )
            )

            if isinstance(review_res, dict) and "id" in review_res and channel:
                try:
                    rev_msg = await channel.fetch_message(int(review_res["id"]))
                    await rev_msg.add_reaction(emoji_partial("serce"))
                except Exception:
                    pass

            sticky_res = await send_v2_container(
                bot,
                interaction.channel_id,
                build_wystaw_opinie_panel_components()
            )
            if isinstance(sticky_res, dict) and "id" in sticky_res:
                db_set_setting("opinie_sticky_msg_id", str(sticky_res["id"]))

            db_set_setting("opinie_channel_id", str(interaction.channel_id))
            new_opinie_count = db_increment_setting("total_opinie_count", 1)

            if isinstance(channel, discord.abc.GuildChannel):
                asyncio.create_task(
                    safe_rename_channel(channel, f"💜・opinie・klientów➔{new_opinie_count}", force=False)
                )

            await interaction.followup.send(
                f"{E['yes_box']} Dziękujemy! Twoja opinia została opublikowana.",
                ephemeral=True
            )

        elif cid == "modal_zakup_submit":
            await interaction.response.defer(ephemeral=True)
            fields, _ = extract_modal_values(interaction.data)
            produkt = fields.get("produkt", "Brak")
            ilosc = fields.get("ilosc", "1")
            platnosc = fields.get("platnosc", "BLIK")
            kod = fields.get("kod_znizkowy", "")
            kod_reklamacji = generuj_kod_reklamacji()

            guild = interaction.guild
            category = guild.get_channel(CATEGORY_ZAKUP_ID)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    read_message_history=True
                )
            }

            channel = await guild.create_text_channel(
                name=f"🛒・zakup-{interaction.user.name[:12]}",
                category=category,
                topic=f"ticket_owner:{interaction.user.id}|kod:{kod_reklamacji}",
                overwrites=overwrites
            )

            ACTIVE_TICKETS[interaction.user.id] = channel.id
            TICKET_TRANSCRIPTS[channel.id] = [
                f"--- Otwarto Ticket Zakupowy przez {interaction.user} ({interaction.user.id}) ---",
                f"--- Produkt: {produkt} | Ilość: {ilosc} | Płatność: {platnosc} | Kod zniżkowy: {kod if kod else 'Brak'} ---"
            ]
            TICKET_METADATA[channel.id] = {
                "owner_id": interaction.user.id,
                "typ": "zakup",
                "produkt": produkt,
                "ilosc": ilosc,
                "platnosc": platnosc,
                "kod": kod if kod else "Brak",
                "kod_reklamacji": kod_reklamacji,
                "claimed_by": None,
                "kwota": "-"
            }

            await send_v2_container(
                bot,
                channel.id,
                build_opened_ticket_components(
                    interaction.user,
                    produkt,
                    ilosc,
                    platnosc,
                    kod,
                    kod_reklamacji
                )
            )
            await interaction.followup.send(
                f"{E['yes_box']} **Formularz Zakupu** został wysłany! Przejdź do swojego ticketa: {channel.mention}",
                ephemeral=True
            )

        elif cid == "modal_reklamacja_submit":
            await interaction.response.defer(ephemeral=True)
            fields, attachment_urls = extract_modal_values(interaction.data)
            kod_rek = fields.get("kod_reklamacji", "Brak")
            data_zam = fields.get("data_zamkniecia", "Brak")
            produkt = fields.get("zakupiony_produkt", "Brak")
            sprzedawca = fields.get("sprzedawca", "Brak")

            guild = interaction.guild
            category = guild.get_channel(CATEGORY_POMOC_ID)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    read_message_history=True
                )
            }

            if sprzedawca.isdigit():
                seller_member = guild.get_member(int(sprzedawca))
                if seller_member:
                    overwrites[seller_member] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True
                    )

            channel = await guild.create_text_channel(
                name=f"🚨・reklamacja-{interaction.user.name[:10]}",
                category=category,
                topic=f"ticket_owner:{interaction.user.id}|kod:{kod_rek}",
                overwrites=overwrites
            )

            ACTIVE_TICKETS[interaction.user.id] = channel.id
            TICKET_TRANSCRIPTS[channel.id] = [
                f"--- Otwarto Ticket Reklamacyjny przez {interaction.user} ({interaction.user.id}) ---",
                f"--- Kod Reklamacji: {kod_rek} | Data: {data_zam} | Produkt: {produkt} | Sprzedawca ID: {sprzedawca} ---"
            ]
            TICKET_METADATA[channel.id] = {
                "owner_id": interaction.user.id,
                "typ": "reklamacja",
                "produkt": f"Reklamacja: {produkt}",
                "ilosc": "1",
                "platnosc": "-",
                "kod": "-",
                "kod_reklamacji": kod_rek,
                "claimed_by": int(sprzedawca) if sprzedawca.isdigit() else None,
                "kwota": "-"
            }

            await send_v2_container(
                bot,
                channel.id,
                build_complaint_ticket_components(
                    interaction.user,
                    kod_rek,
                    data_zam,
                    produkt,
                    sprzedawca,
                    attachment_urls
                )
            )
            await interaction.followup.send(
                f"{E['yes_box']} **Formularz Reklamacji** został wysłany! Przejdź do swojego ticketa: {channel.mention}",
                ephemeral=True
            )

# ==============================================================================
# 16. KOMENDY ROZLICZENIOWE DLA SPRZEDAWCÓW I WŁAŚCICIELI
# ==============================================================================
@bot.tree.command(
    name="rozliczenie",
    description="Sprawdź swoje tygodniowe rozliczenie sprzedawcy (30% tygodniowo Twoich zarobków)"
)
@app_commands.describe(
    sprzedawca="Opcjonalnie: oznacz sprzedawcę, którego rozliczenie chcesz sprawdzić"
)
async def cmd_rozliczenie(interaction: discord.Interaction, sprzedawca: Optional[discord.Member] = None):
    await interaction.response.defer(ephemeral=True)
    target_member = sprzedawca if sprzedawca else interaction.user
    stats = db_get_seller_settlement(target_member.id)
    embed = build_seller_individual_settlement_embed(target_member, stats)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(
    name="adminrozliczenia",
    description="Wyświetla listę wszystkich sprzedawców (ranga 1539238412865900554) i ich tygodniowe 30% dla Zarządu"
)
@app_commands.default_permissions(administrator=True)
async def cmd_adminrozliczenia(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = build_admin_all_settlements_embed(interaction.guild)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(
    name="resetujrozliczenia",
    description="Resetuje tygodniowe rozliczenia wszystkich sprzedawców (lub wybranego sprzedawcy)"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    sprzedawca="Opcjonalnie: wybierz jednego sprzedawcę do zresetowania (zostaw puste, aby zresetować wszystkich)"
)
async def cmd_resetujrozliczenia(interaction: discord.Interaction, sprzedawca: Optional[discord.Member] = None):
    await interaction.response.defer(ephemeral=True)
    if sprzedawca is not None:
        db_reset_seller_settlements(seller_id=sprzedawca.id)
        await interaction.followup.send(
            f"{E['yes_box']} Pomyślnie zresetowano tygodniowe rozliczenie dla sprzedawcy {sprzedawca.mention}!",
            ephemeral=True
        )
    else:
        db_reset_seller_settlements(seller_id=None)
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        await interaction.followup.send(
            f"{E['yes_box']} **Wszystkie tygodniowe rozliczenia sprzedawców zostały wyzerowane!**\n"
            f"> {E['kalendarz']} Nowy tydzień rozliczeniowy rozpoczął się: **`{now_str}`**",
            ephemeral=True
        )

@bot.tree.command(
    name="panel_rozliczenia",
    description="Wysyła Panel Rozliczeniowy Sprzedawców z przyciskiem Moje Statystyki"
)
@app_commands.default_permissions(administrator=True)
async def cmd_panel_rozliczenia(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await send_v2_container(bot, interaction.channel_id, build_seller_settlement_panel_components())
        await interaction.followup.send(
            f"{E['yes_box']} **Panel Rozliczeniowy Sprzedawców** został wysłany na ten kanał!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

# ==============================================================================
# 17. KOMENDA /zrealizowano ORAZ KOMENDY ZARZĄDZANIA STATYSTYKAMI
# ==============================================================================
@bot.tree.command(
    name="zrealizowano",
    description="Oznacza zamówienie jako zrealizowane, dolicza do tygodniowych zarobków i generuje wzór +rep"
)
@app_commands.describe(
    kwota="Kwota w PLN (np. 18.00)",
    produkt="Nazwa zakupionego produktu (opcjonalnie - domyślnie pobiera z formularza ticketa)",
    ilosc="Ilość sztuk (opcjonalnie - domyślnie pobiera z formularza ticketa)",
    metoda="Metoda płatności (opcjonalnie - domyślnie pobiera z formularza ticketa)"
)
async def cmd_zrealizowano(
    interaction: discord.Interaction,
    kwota: str,
    produkt: Optional[str] = None,
    ilosc: Optional[str] = None,
    metoda: Optional[str] = None
):
    seller_role = interaction.guild.get_role(ROLE_SPRZEDAWCA_ID) if interaction.guild else None
    has_seller_role = (seller_role in interaction.user.roles) if (seller_role and isinstance(interaction.user, discord.Member)) else False

    if not interaction.user.guild_permissions.manage_messages and not has_seller_role:
        return await interaction.response.send_message(
            f"{E['x']} Tylko sprzedawcy (<@&{ROLE_SPRZEDAWCA_ID}>) oraz administracja mogą użyć komendy `/zrealizowano`!",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    meta = TICKET_METADATA.get(interaction.channel_id, {})

    final_produkt = produkt if produkt else meta.get("produkt", "Produkt")
    final_ilosc = ilosc if ilosc else meta.get("ilosc", "1")
    final_metoda = (metoda if metoda else meta.get("platnosc", "BLIK")).upper()

    clean_kwota_str = kwota.upper().replace("PLN", "").replace("ZŁ", "").replace("ZL", "").replace(",", ".").strip()
    try:
        numeric_kwota = round(float(clean_kwota_str), 2)
        final_kwota = f"{numeric_kwota:.2f} PLN"
    except ValueError:
        numeric_kwota = 0.0
        final_kwota = f"{clean_kwota_str} PLN"

    if interaction.channel_id in TICKET_METADATA:
        TICKET_METADATA[interaction.channel_id]["produkt"] = final_produkt
        TICKET_METADATA[interaction.channel_id]["ilosc"] = str(final_ilosc)
        TICKET_METADATA[interaction.channel_id]["platnosc"] = final_metoda
        TICKET_METADATA[interaction.channel_id]["kwota"] = final_kwota
        TICKET_METADATA[interaction.channel_id]["claimed_by"] = interaction.user.id

    owner_id = meta.get("owner_id")
    if not owner_id and interaction.channel.topic and "ticket_owner:" in interaction.channel.topic:
        try:
            owner_id = int(interaction.channel.topic.split("ticket_owner:")[1].split("|")[0])
        except Exception:
            owner_id = None

    # Doliczamy kwotę do łącznych tygodniowych zarobków sprzedawcy!
    if numeric_kwota > 0:
        db_add_seller_sale(interaction.user.id, numeric_kwota)
        if owner_id:
            db_set_pending_order(owner_id, numeric_kwota, final_produkt, interaction.user.id, seller_settled=1)

    klient_mention = f"<@{owner_id}>" if owner_id else "Kliencie"
    kod_rek = meta.get("kod_reklamacji", generuj_kod_reklamacji())

    gotowy_rep = f"+rep {interaction.user.mention} x{final_ilosc} {final_produkt} [{final_metoda}] [{final_kwota}]"

    zrealizowano_components = [
        {
            "type": 10,
            "content": f"```\n           {SHOP_NAME} × ZAMÓWIENIE ZREALIZOWANE\n```"
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"> {E['yes_box']} ' **Dziękujemy za zakup, {klient_mention}!** Twoje zamówienie zostało zrealizowane przez {interaction.user.mention}.\n"
                f"> {E['box']} ' **Produkt:** `x{final_ilosc} {final_produkt}`\n"
                f"> {E['pay']} ' **Opłacono:** `{final_kwota}` (`{final_metoda}`)\n"
                f"> {E['hasztag']} ' **Kod Reklamacji:** `{kod_rek}`"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": (
                f"### {E['lupa']} ' Wystaw opinię (+rep), aby zamknąć ticket i odebrać rangę klienta!\n"
                f"Skopiuj **gotową wiadomość poniżej** i wyślij ją na kanale <#{LEGIT_CHECK_CHANNEL_ID}>:\n"
                f"```\n{gotowy_rep}\n```\n"
                f"> {E['strzalka']} ` {gotowy_rep} `\n\n"
                f"-# Po wysłaniu powyższego +rep kwota `{final_kwota}` automatycznie doliczy się do Twoich statystyk, a ticket się zamknie!"
            )
        },
        {"type": 14, "divider": True, "spacing": 1},
        {
            "type": 10,
            "content": f"-# {E['koszyk']} © 2026 {SHOP_NAME} × Realizacja Zamówień"
        }
    ]

    try:
        await send_v2_container(bot, interaction.channel_id, zrealizowano_components)
        if interaction.channel_id in TICKET_TRANSCRIPTS:
            TICKET_TRANSCRIPTS[interaction.channel_id].append(
                f"--- ZREALIZOWANO ZAMÓWIENIE przez {interaction.user}: {gotowy_rep} ---"
            )
        seller_stats = db_get_seller_settlement(interaction.user.id)
        await interaction.followup.send(
            f"{E['yes_box']} Wysłano podsumowanie realizacji wraz z gotowym wzorem `+rep`!\n"
            f"> {E['pieniadze']} Doliczono **`+{numeric_kwota:.2f} PLN`** do Twoich tygodniowych zarobków (Łącznie w tym tygodniu: `{seller_stats['turnover']:.2f} PLN` | Rozliczenie tygodniowe 30% dla Zarządu: `{seller_stats['due_to_owners']:.2f} PLN`).",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd wysyłania panelu realizacji: `{e}`", ephemeral=True)

@bot.tree.command(name="dodaj_wydane", description="Dodaje wydaną kwotę PLN do statystyk klienta i aktualizuje jego rangę")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(klient="Klient, któremu chcesz dodać wydaną kwotę", kwota="Kwota w PLN do dodania (np. 30.00)")
async def cmd_dodaj_wydane(interaction: discord.Interaction, klient: discord.Member, kwota: float):
    await interaction.response.defer(ephemeral=True)
    new_total = db_add_client_spent(klient.id, kwota)
    role_id = await sync_member_client_roles(klient, new_total)
    asyncio.create_task(update_all_live_channels(bot, interaction.guild, force=False))
    ranga_txt = f"<@&{role_id}>" if role_id else "Brak"
    await interaction.followup.send(
        f"{E['yes_box']} Dodano **`{kwota:.2f} PLN`** dla {klient.mention}!\n"
        f"> {E['portfel']} Łącznie wydane: **`{new_total:.2f} PLN`**\n"
        f"> {E['klient_500']} Aktualna ranga: {ranga_txt}",
        ephemeral=True
    )

@bot.tree.command(name="ustaw_wydane", description="Ustawia dokładną wydaną kwotę PLN dla klienta i aktualizuje jego rangę")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(klient="Klient, któremu chcesz ustawić wydaną kwotę", kwota="Nowa łączna kwota w PLN (np. 100.00)")
async def cmd_ustaw_wydane(interaction: discord.Interaction, klient: discord.Member, kwota: float):
    await interaction.response.defer(ephemeral=True)
    new_total = db_set_client_spent(klient.id, kwota)
    role_id = await sync_member_client_roles(klient, new_total)
    asyncio.create_task(update_all_live_channels(bot, interaction.guild, force=False))
    ranga_txt = f"<@&{role_id}>" if role_id else "Brak"
    await interaction.followup.send(
        f"{E['yes_box']} Ustawiono łączne wydatki {klient.mention} na **`{new_total:.2f} PLN`**!\n"
        f"> {E['klient_500']} Aktualna ranga: {ranga_txt}",
        ephemeral=True
    )

@bot.tree.command(name="odswiez_statystyki", description="Natychmiast odświeża nazwy wszystkich kanałów statystyk VC oraz liczników")
@app_commands.default_permissions(administrator=True)
async def cmd_odswiez_statystyki(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await update_all_live_channels(bot, interaction.guild, force=True)
    await update_or_send_daily_lc_message(bot)
    await interaction.followup.send(
        f"{E['yes_box']} Wszystkie kanały statystyk głosowych, liczniki i Dzienne LC zostały odświeżone!",
        ephemeral=True
    )

# ==============================================================================
# 18. KOMENDY WYSYŁAJĄCE PANELE V2 (POWITALNIA, LC, DZIENNE LC, CZY LEGIT, SZUKAJ, OPINIE)
# ==============================================================================
@bot.tree.command(name="test_powitanie", description="Wysyła powitanie 1:1 Components V2")
@app_commands.default_permissions(administrator=True)
async def cmd_test_powitanie(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await send_v2_container(
            bot,
            interaction.channel_id,
            build_welcome_components(interaction.user, interaction.guild)
        )
        await interaction.followup.send(f"{E['yes_box']} Powitanie V2 wysłane!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_lc", description="Wysyła panel wzoru Legit Check 1:1")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_lc(interaction: discord.Interaction):
    global LAST_LC_STICKY_MESSAGE_ID
    await interaction.response.defer(ephemeral=True)
    try:
        res = await send_v2_container(bot, interaction.channel_id, build_legit_check_components())
        if isinstance(res, dict) and "id" in res:
            LAST_LC_STICKY_MESSAGE_ID = int(res["id"])
            db_set_setting("lc_sticky_msg_id", str(LAST_LC_STICKY_MESSAGE_ID))
        await interaction.followup.send(f"{E['yes_box']} Panel LC wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_dzienne_lc", description="Wysyła lub odświeża raport Dzienne LC na kanale 1539238564926197872")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_dzienne_lc(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await update_or_send_daily_lc_message(bot)
        await interaction.followup.send(
            f"{E['yes_box']} Panel **Dzienne LC** został wysłany/zaktualizowany na kanale <#{DZIENNE_LC_CHANNEL_ID}>!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_czy_legit", description="Wysyła panel Czy Jesteśmy Legit z reakcjami i licznikiem w nazwie kanału")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_czy_legit(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        res = await send_v2_container(bot, interaction.channel_id, build_czy_legit_components())
        if isinstance(res, dict) and "id" in res:
            msg_id = int(res["id"])
            db_set_setting("czy_legit_msg_id", str(msg_id))
            db_set_setting("czy_legit_channel_id", str(interaction.channel_id))
            msg = await interaction.channel.fetch_message(msg_id)
            await msg.add_reaction(emoji_partial("yes_box"))
            await msg.add_reaction(emoji_partial("no_check"))
        await interaction.followup.send(f"{E['yes_box']} Panel **Czy Jesteśmy Legit** wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_wyszukaj", description="Wysyła panel Wyszukiwania Produktów po nazwie")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_wyszukaj(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await send_v2_container(bot, interaction.channel_id, build_search_product_panel_components())
        await interaction.followup.send(f"{E['yes_box']} Panel **Wyszukiwania Produktów** wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_opinie", description="Wysyła panel Wystaw Opinię (z formularzem gwiazdek i licznikiem)")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_opinie(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        res = await send_v2_container(bot, interaction.channel_id, build_wystaw_opinie_panel_components())
        if isinstance(res, dict) and "id" in res:
            db_set_setting("opinie_sticky_msg_id", str(res["id"]))
            db_set_setting("opinie_channel_id", str(interaction.channel_id))
        await interaction.followup.send(f"{E['yes_box']} Panel **Wystaw Opinię** wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_tickety", description="Wysyła panel Ticketów 1:1")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_tickety(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await send_v2_container(bot, interaction.channel_id, build_tickets_panel_components())
        await interaction.followup.send(f"{E['yes_box']} Panel Ticketów wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_klienta", description="Wysyła Panel Klienta 1:1")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_klienta(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await send_v2_container(bot, interaction.channel_id, build_client_panel_components())
        await interaction.followup.send(f"{E['yes_box']} Panel Klienta wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

@bot.tree.command(name="panel_produkty", description="Wysyła Panel Cennika (Nasze Produkty) 1:1")
@app_commands.default_permissions(administrator=True)
async def cmd_panel_produkty(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await send_v2_container(bot, interaction.channel_id, build_products_panel_components())
        await interaction.followup.send(f"{E['yes_box']} Panel Cennika (Nasze Produkty) wysłany!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Błąd API Discorda: `{e}`", ephemeral=True)

# ==============================================================================
# 19. BEZPIECZNY START BOTA (ZABEZPIECZENIE PRZED CLOUDFLARE 1015)
# ==============================================================================
async def main():
    await web_server()

    while True:
        try:
            await bot.start(TOKEN)
        except discord.HTTPException as e:
            print(f"⚠️ Limit zapytań Discord / Cloudflare (HTTP {e.status}). Odczekuję 5 minut przed ponowną próbą...")
            await asyncio.sleep(300)
        except Exception as e:
            print(f"❌ Błąd połączenia: {e}. Ponowna próba za 60 sekund...")
            await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())