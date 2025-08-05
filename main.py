import asyncio
import os
from typing import Optional, Tuple, List

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page
from openpyxl import Workbook

# Load credentials from .env
load_dotenv()
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')

INPUT_FILE = 'ids_shot_4_image.txt'
OUTPUT_FILE = 'hotel_questions.xlsx'


class AuthService:
    def __init__(self, page: Page):
        self.page = page

    async def login(self):
        await self.page.goto("https://tophotels.pro/auth/login", timeout=20000)
        await self.page.wait_for_selector('input[name="email"]', timeout=10000)
        await self.page.fill('input[name="email"]', EMAIL)
        await self.page.fill('input[name="password"]', PASSWORD)
        await self.page.click('button[type="submit"]')
        await asyncio.sleep(2)
        # await self.page.wait_for_selector("text=КЛУБ ТОПХОТЕЛС", timeout=10000)


class HotelParser:
    def __init__(self, page: Page):
        self.page = page

    async def get_hotel_info(self, hotel_id: str) -> Tuple[str, str, int]:
        url = f'https://tophotels.ru/hotel/al{hotel_id}/questions'
        await self.page.goto(url, timeout=15000)

        try:
            title = await self._get_text_or_default('h1', f'al{hotel_id}')
            questions_text = await self._get_text_or_default('#container > article > h2', '')
            count = int(''.join(filter(str.isdigit, questions_text))) if questions_text else 0
            return hotel_id, title.strip(), count
        except Exception as e:
            print(f"[ERROR questions] al{hotel_id}: {e}")
            return hotel_id, 'Ошибка', 0

    async def get_ratings(self, hotel_id: str) -> Tuple[Optional[float], Optional[float]]:
        url = f'https://tophotels.ru/hotel/al{hotel_id}/reviews'
        await self.page.goto(url, timeout=15000)

        try:
            await self.page.wait_for_selector('.card-hotel-rating-statistic', timeout=10000)
            blocks = await self.page.query_selector_all('.card-hotel-rating-statistic .card-hotel-rating')

            overall, y2025 = None, None
            for block in blocks:
                text = await block.inner_text()
                if "Общий рейтинг" in text:
                    overall = await self._extract_rating(block)
                elif "Рейтинг 2025" in text:
                    y2025 = await self._extract_rating(block)

            return overall, y2025
        except Exception as e:
            print(f"[ERROR ratings] al{hotel_id}: {e}")
            return None, None

    async def _get_text_or_default(self, selector: str, default: str) -> str:
        element = await self.page.query_selector(selector)
        return await element.inner_text() if element else default

    async def _extract_rating(self, block) -> Optional[float]:
        span = await block.query_selector('b span')
        if span:
            rating_text = await span.inner_text()
            return float(rating_text.replace(',', '.').strip())
        return None


class ExcelExporter:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.workbook = Workbook()
        self.sheet = self.workbook.active
        self.sheet.title = "Вопросы"
        self.sheet.append(['ID', 'Название', 'Количество вопросов', 'Общий рейтинг', 'Рейтинг 2025'])

    def add_row(self, row: List):
        self.sheet.append(row)

    def save(self):
        self.workbook.save(self.file_path)


class HotelScraperApp:
    def __init__(self, hotel_ids: List[str]):
        self.hotel_ids = hotel_ids

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
            page = await context.new_page()

            auth_service = AuthService(page)
            await auth_service.login()

            parser = HotelParser(page)
            exporter = ExcelExporter(OUTPUT_FILE)

            for hotel_id in self.hotel_ids:
                hotel_id, title, question_count = await parser.get_hotel_info(hotel_id)
                overall, y2025 = await parser.get_ratings(hotel_id)
                print(f"al{hotel_id}: {title} — {question_count} | общий: {overall}, 2025: {y2025}")

                exporter.add_row([
                    f'al{hotel_id}', title, question_count,
                    overall if overall else '',
                    y2025 if y2025 else ''
                ])

            exporter.save()
            await browser.close()


def load_hotel_ids(path: str) -> List[str]:
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip().isdigit()]


if __name__ == '__main__':
    ids = load_hotel_ids(INPUT_FILE)
    print(ids)
    app = HotelScraperApp(ids)
    asyncio.run(app.run())
