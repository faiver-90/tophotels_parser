import asyncio
import logging

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_PRO, SCREENSHOTS_DIR
from parce_screenshots.moduls.locators import SERVICES_AND_PRICES_LOCATOR, TG_LOCATOR, FLAG_ON_TABLE_FOR_DELETE
from parce_screenshots.utils import hide_tg, delete_locator
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def service_prices(page: Page, hotel_id, hotel_title=None):
    "https://tophotels.pro/al/317844/stat/profile?group=day&vw=grouped"
    try:
        url = BASE_URL_PRO + f"al/{hotel_id[2:]}/stat/profile?group=day&vw=grouped"
        await page.goto(url, timeout=0)

        await hide_tg(page)
        await delete_locator(page, TG_LOCATOR)
        await delete_locator(page, FLAG_ON_TABLE_FOR_DELETE)

        await asyncio.sleep(2)

        await page.wait_for_selector(
            SERVICES_AND_PRICES_LOCATOR, state="visible", timeout=30000
        )

        element = await page.query_selector(SERVICES_AND_PRICES_LOCATOR)

        old_viewport = (
            page.viewport_size
        )  # TODO посмотреть почему не меняется масштаб и падает
        await page.set_viewport_size({"width": 1400, "height": 1000})
        await element.screenshot(
            path=get_screenshot_path(hotel_id, hotel_title, "06_service_prices.png")
        )
        await page.set_viewport_size(old_viewport)
    except Exception as e:
        logging.exception(f"[service_prices] Ошибка при выполнении {url}")
