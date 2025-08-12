import logging

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import SCREENSHOTS_DIR, BASE_URL_TH
from parce_screenshots.moduls.locators import REVIEW_LOCATOR, COUNT_REVIEW_LOCATOR, TG_LOCATOR, FLAG_ON_TABLE_FOR_DELETE
from parce_screenshots.utils import delete_locator
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def review_screen(page: Page, hotel_id, hotel_title=None):
    try:
        "https://tophotels.ru/en/hotel/al27382/reviews"
        url = BASE_URL_TH + "hotel/" + hotel_id + "/reviews"
        await page.goto(url, timeout=0)

        await page.wait_for_selector(REVIEW_LOCATOR, state="visible", timeout=30000)
        await delete_locator(page, TG_LOCATOR)
        await delete_locator(page, FLAG_ON_TABLE_FOR_DELETE)

        element = await page.query_selector(REVIEW_LOCATOR)
        await element.screenshot(
            path=get_screenshot_path(hotel_id, hotel_title, "03_reviews.png")
        )

        return await page.locator(COUNT_REVIEW_LOCATOR).text_content()
    except Exception as e:
        logging.exception(f"[review_screen] Ошибка при выполнении {url}")
