"""
PepeRush Bot — Database Layer (SQLite WAL, thread-safe)
"""
import sqlite3
import time
import logging
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         INTEGER PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                balance         INTEGER DEFAULT 0,
                referrer_id     INTEGER,
                referral_count  INTEGER DEFAULT 0,
                wallet          TEXT,
                joined_channels INTEGER DEFAULT 0,
                human_verified  INTEGER DEFAULT 0,
                last_daily      REAL    DEFAULT 0,
                last_withdraw   REAL    DEFAULT 0,
                joined_at       REAL    DEFAULT 0,
                is_banned       INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS referral_pending (
                new_user_id  INTEGER PRIMARY KEY,
                referrer_id  INTEGER NOT NULL,
                created_at   REAL    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS referral_rewarded (
                new_user_id  INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS withdrawals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                amount       INTEGER NOT NULL,
                wallet       TEXT    NOT NULL,
                status       TEXT    DEFAULT 'pending',
                requested_at REAL    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                platform  TEXT    NOT NULL,
                link      TEXT    UNIQUE NOT NULL,
                chat_id   TEXT,
                is_active INTEGER DEFAULT 1,
                added_at  REAL    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suspicious_log (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event   TEXT,
                ts      REAL
            );
        """)
        _seed_defaults(conn)
    logger.info("✅ Database ready.")


def _seed_defaults(conn):
    now = time.time()
    defaults = [
        ("telegram", "https://t.me/+r-RTbZy7RT81NTdk",                          None),
        ("telegram", "https://t.me/+etPGyK-JcLwxZDY0",                          None),
        ("telegram", "https://t.me/+8SimTcYDCJllMjI0",                          None),
        ("telegram", "https://t.me/+H6oH96FgLi44ZDVk",                          None),
        ("whatsapp", "https://chat.whatsapp.com/HR1SaRJkPlJ3tWPsWldcPv?mode=gi_t", None),
        ("whatsapp", "https://chat.whatsapp.com/EMY3Mx7dkhfF8FsBytfSx2?mode=gi_t", None),
        ("whatsapp", "https://chat.whatsapp.com/EMY3Mx7dkhfF8FsBytfSx2?mode=gi_f", None),
        ("whatsapp", "https://chat.whatsapp.com/EMY3Mx7dkhfF8FsBytfSx2?mode=gi_g", None),
    ]
    for plat, link, cid in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO tasks (platform,link,chat_id,added_at) VALUES (?,?,?,?)",
            (plat, link, cid, now)
        )


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def upsert_user(user_id: int, username: str, first_name: str):
    now = time.time()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id,username,first_name,joined_at)
            VALUES (?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (user_id, username, first_name, now))

def set_human_verified(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET human_verified=1 WHERE user_id=?", (user_id,))

def set_joined_channels(user_id: int, value: int = 1):
    with get_conn() as conn:
        conn.execute("UPDATE users SET joined_channels=? WHERE user_id=?", (value, user_id))

def get_balance(user_id: int) -> int:
    with get_conn() as conn:
        r = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
        return r["balance"] if r else 0

def add_balance(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))

def deduct_balance(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, user_id))

def set_wallet(user_id: int, wallet: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET wallet=? WHERE user_id=?", (wallet, user_id))

def set_last_daily(user_id: int, ts: float):
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_daily=? WHERE user_id=?", (ts, user_id))

def set_last_withdraw(user_id: int, ts: float):
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_withdraw=? WHERE user_id=?", (ts, user_id))

def get_all_user_ids() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE is_banned=0 AND human_verified=1"
        ).fetchall()
        return [r["user_id"] for r in rows]

def get_stats() -> dict:
    with get_conn() as conn:
        tu  = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        tw  = conn.execute("SELECT COUNT(*) as c FROM withdrawals").fetchone()["c"]
        pw  = conn.execute("SELECT COUNT(*) as c FROM withdrawals WHERE status='pending'").fetchone()["c"]
        tot = conn.execute("SELECT COALESCE(SUM(amount),0) as s FROM withdrawals WHERE status='done'").fetchone()["s"]
        return {"total_users": tu, "total_withdrawals": tw, "pending_withdrawals": pw, "total_pepe_out": tot}

def ban_user(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))


# ── Referrals ─────────────────────────────────────────────────────────────────

def set_referrer(new_user_id: int, referrer_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET referrer_id=? WHERE user_id=? AND referrer_id IS NULL",
            (referrer_id, new_user_id)
        )

def add_referral_pending(new_user_id: int, referrer_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO referral_pending (new_user_id,referrer_id,created_at) VALUES (?,?,?)",
            (new_user_id, referrer_id, time.time())
        )

def get_referral_pending(new_user_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM referral_pending WHERE new_user_id=?", (new_user_id,)
        ).fetchone()

def is_referral_rewarded(new_user_id: int) -> bool:
    with get_conn() as conn:
        return bool(conn.execute(
            "SELECT 1 FROM referral_rewarded WHERE new_user_id=?", (new_user_id,)
        ).fetchone())

def mark_referral_rewarded(new_user_id: int, referrer_id: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO referral_rewarded (new_user_id) VALUES (?)", (new_user_id,))
        conn.execute("DELETE FROM referral_pending WHERE new_user_id=?", (new_user_id,))
        conn.execute("UPDATE users SET referral_count=referral_count+1 WHERE user_id=?", (referrer_id,))

def get_leaderboard(limit: int = 10) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT user_id,username,first_name,referral_count FROM users "
            "ORDER BY referral_count DESC LIMIT ?", (limit,)
        ).fetchall()


# ── Withdrawals ───────────────────────────────────────────────────────────────

def create_withdrawal(user_id: int, amount: int, wallet: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO withdrawals (user_id,amount,wallet,requested_at) VALUES (?,?,?,?)",
            (user_id, amount, wallet, time.time())
        )
        return cur.lastrowid

def has_pending_withdrawal(user_id: int) -> bool:
    with get_conn() as conn:
        return bool(conn.execute(
            "SELECT 1 FROM withdrawals WHERE user_id=? AND status='pending'", (user_id,)
        ).fetchone())


# ── Tasks ─────────────────────────────────────────────────────────────────────

def get_active_tasks() -> list:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tasks WHERE is_active=1 ORDER BY id").fetchall()

def get_telegram_tasks() -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tasks WHERE is_active=1 AND platform='telegram' ORDER BY id"
        ).fetchall()

def add_task(platform: str, link: str, chat_id: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tasks (platform,link,chat_id,added_at) VALUES (?,?,?,?)",
            (platform, link, chat_id, time.time())
        )

def update_task_chat_id(link: str, chat_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET chat_id=? WHERE link=?", (chat_id, link))

def remove_task(link: str):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET is_active=0 WHERE link=?", (link,))

def reset_all_joined():
    with get_conn() as conn:
        conn.execute("UPDATE users SET joined_channels=0 WHERE human_verified=1 AND is_banned=0")


# ── Suspicious log ────────────────────────────────────────────────────────────

def log_suspicious(user_id: int, event: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO suspicious_log (user_id,event,ts) VALUES (?,?,?)",
            (user_id, event, time.time())
        )

def get_suspicious_count(user_id: int, event: str, window: int = 3600) -> int:
    since = time.time() - window
    with get_conn() as conn:
        r = conn.execute(
            "SELECT COUNT(*) as c FROM suspicious_log WHERE user_id=? AND event=? AND ts>?",
            (user_id, event, since)
        ).fetchone()
        return r["c"] if r else 0
