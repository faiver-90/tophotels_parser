import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

from utils import load_hotel_ids

load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent

CURRENT_MONTH = os.getenv("CURRENT_MONTH") or datetime.now().strftime("%B")
CURRENT_YEAR  = os.getenv("CURRENT_YEAR")  or datetime.now().strftime("%Y")

file_handler = RotatingFileHandler(
    SCRIPT_DIR / "script.log",
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        file_handler,
        logging.StreamHandler(),
    ],
)

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

OUTPUT_FILE_COUNTER_REVIEW = os.getenv(
    "OUTPUT_FILE_COUNTER_REVIEW", "hotel_questions.xlsx"
)

SCREENSHOTS_DIR = SCRIPT_DIR / "screenshots"

BASE_URL_TH = os.getenv("BASE_URL_TH", "https://tophotels.ru/en/")
BASE_URL_PRO = os.getenv("BASE_URL_PRO", "https://ssa.tophotels.pro/")
HOTELS_IDS_FILE = os.getenv("HOTELS_IDS_FILE", "ids.txt")

DELAY_FOR_DELETE = int(os.getenv("DELAY_FOR_DELETE", 500))
RETRIES_FOR_DELETE_LOCATORS = int(os.getenv("RETRIES_FOR_DELETE_LOCATORS", 3))

HEADLESS = os.getenv("HEADLESS", "True").strip().lower() == "true"

CONCURRENCY = int(os.getenv("CONCURRENCY", "1"))
AUTH_STATE = Path("auth_state.json")

MAX_ATTEMPTS_RUN = int(os.getenv("MAX_ATTEMPTS_RUN", 5))
MAX_FIRST_RUN = int(os.getenv("MAX_FIRST_RUN", 2))

SLEEP = os.getenv("SLEEP", "False").strip().lower() == "true"

RESOLUTION_H = int(os.getenv("RESOLUTION_H", 1000))
RESOLUTION_W = int(os.getenv("RESOLUTION_W", 1005))

PAGE_BREAK_FILES = {"07_rating_in_hurghada.png", "08_activity.png", "04_attendance.png"}
ENABLED_SHOTS = ["01_top_element.png",
                 "02_populars_element.png",
                 "03_reviews.png",
                 "04_attendance.png",
                 "06_service_prices.png",
                 "07_rating_in_hurghada.png",
                 "08_activity.png"]
# Word
FONT_NAME = "Roboto"
FONT_SIZE_TITLE = 12
FONT_SIZE_HOTEL_LINK = 12
FONT_SIZE_CAPTION = 13

IMAGE_WIDTH_INCHES = 6  # ширина вставки в DOCX (это не пиксели файла; файл мы теперь можем заранее привести)
URL_RE = re.compile(r"(https?://[^\s)]+)")
