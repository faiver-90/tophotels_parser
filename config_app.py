import os

from dotenv import load_dotenv

load_dotenv()
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')

OUTPUT_FILE_COUNTER_REVIEW = 'hotel_questions.xlsx'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(SCRIPT_DIR, "01_screenshots")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "00_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

BASE_URL_RU = 'https://tophotels.ru/en/'
BASE_URL_PRO = 'https://tophotels.pro/'
HOTELS_IDS_FILE = 'ids.txt'

MAX_ATTEMPTS_RUN = 20
