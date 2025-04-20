import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
GSHEET_JSON = os.getenv("GSHEET_JSON")
GSHEET_NAME_ORDERS = os.getenv("GSHEET_NAME_ORDERS")
GSHEET_NAME_STOCK = os.getenv("GSHEET_NAME_STOCK")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
AUTO_ORDER_EMAIL = [i.strip() for i in os.getenv("AUTO_ORDER_EMAIL", "").split(",") if i.strip()]
LOG_FILE = os.getenv("LOG_FILE", "bot.log")