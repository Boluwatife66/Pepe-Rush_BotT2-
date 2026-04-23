"""
PepeRush Bot — Configuration
"""
import os

BOT_TOKEN: str       = "8715232497:AAHZ5_l_NYoAWy8JxdiKyVtFDm_qa2tyFEY"
ADMIN_ID: int        = 8309843074

# Economy
REFERRAL_REWARD: int   = 10_000
DAILY_BONUS: int       = 1_000
MIN_WITHDRAW: int      = 50_000
DAILY_COOLDOWN: int    = 86_400   # 24 h
WITHDRAW_COOLDOWN: int = 3_600    # 1 h
REFERRAL_DELAY: int    = 30       # anti-bot seconds

# Payout channel
PAYOUT_CHANNEL: str    = "https://t.me/+H6oH96FgLi44ZDVk"
PAYOUT_CHANNEL_ID: int = 0  # Set via /getchatid — e.g. -1001234567890

# Database
DB_PATH: str = os.getenv("DB_PATH", "peperush.db")

# Network timeouts (fixes TimedOut on slow connections)
CONNECT_TIMEOUT: int = 30
READ_TIMEOUT: int    = 30
WRITE_TIMEOUT: int   = 30
POOL_TIMEOUT: int    = 30

# Wallet
WALLET_NETWORK: str = "Solana"
WALLET_TOKEN: str   = "BONK"

# Warning text
WARNING_TEXT: str = (
    "⚠️ <b>IMPORTANT WARNING</b>\n\n"
    "Do <b>NOT</b> leave any required channels after joining.\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🚫 Leaving = Withdrawal <b>PERMANENTLY BLOCKED</b>\n"
    "🔍 Membership checked on <b>every single action</b>\n"
    "━━━━━━━━━━━━━━━━━━━━"
)
