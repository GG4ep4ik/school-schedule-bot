import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8615610953:AAEXSvPCrCmL7JdVSEvNXNjf33enqVH0Ymk")

# Schedule Source Configuration
USE_LOCAL_FILE = os.getenv("USE_LOCAL_FILE", "true").lower() == "true"
LOCAL_SCHEDULE_FILE = os.getenv("LOCAL_SCHEDULE_FILE", "Расписание.xlsx")

# Google Sheets Configuration (опционально, если USE_LOCAL_FILE=false)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Расписание")
CREDENTIALS_FILE = "credentials.json"

# Database Configuration
DATABASE_PATH = "data/users.db"

# Scheduler Configuration
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))

# Days of week
DAYS_OF_WEEK = {
    "Понедельник": 0,
    "Вторник": 1,
    "Среда": 2,
    "Четверг": 3,
    "Пятница": 4,
    "Суббота": 5
}

DAYS_LIST = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
