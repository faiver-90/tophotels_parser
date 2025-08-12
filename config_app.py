import logging
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent

curr_month = datetime.now().strftime("%B")  # Полное название месяца, например "August"
curr_year = datetime.now().strftime("%Y")   # Год строкой, например "2025"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / "script.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

load_dotenv()
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')


OUTPUT_FILE_COUNTER_REVIEW = os.getenv('OUTPUT_FILE_COUNTER_REVIEW', 'hotel_questions.xlsx')

SCREENSHOTS_DIR = SCRIPT_DIR / "screenshots"

BASE_URL_TH = os.getenv('BASE_URL_TH', 'https://tophotels.ru/en/')
BASE_URL_PRO = os.getenv('BASE_URL_PRO','https://ssa.tophotels.pro/')
HOTELS_IDS_FILE = os.getenv('HOTELS_IDS_FILE','ids.txt')

MAX_ATTEMPTS_RUN = 20
