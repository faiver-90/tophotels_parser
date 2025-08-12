import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent

curr_month = datetime.now().strftime("%B")
curr_year = datetime.now().strftime("%Y")

file_handler = RotatingFileHandler(
    SCRIPT_DIR / "script.log",
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        file_handler,
        logging.StreamHandler(),
    ],
)

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

OUTPUT_FILE_COUNTER_REVIEW = os.getenv(
    "OUTPUT_FILE_COUNTER_REVIEW", "hotel_questions.xlsx"
)

SCREENSHOTS_DIR = SCRIPT_DIR / "screenshots"

BASE_URL_TH = os.getenv("BASE_URL_TH", "https://tophotels.ru/en/")
BASE_URL_PRO = os.getenv("BASE_URL_PRO", "https://ssa.tophotels.pro/")
HOTELS_IDS_FILE = os.getenv("HOTELS_IDS_FILE", "ids.txt")

DELAY_FOR_DELETE = int(os.getenv('DELAY_FOR_DELETE', 500))
RETRIES_FOR_DELETE_LOCATORS = int(os.getenv('RETRIES_FOR_DELETE_LOCATORS', 3))

HEADLESS = os.getenv('HEADLESS', 'True').strip().lower() == 'true'

MAX_ATTEMPTS_RUN = int(os.getenv('MAX_ATTEMPTS_RUN', 5))
MAX_FIRST_RUN = int(os.getenv('MAX_FIRST_RUN', 2))
