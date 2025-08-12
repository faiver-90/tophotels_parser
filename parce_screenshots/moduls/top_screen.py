import logging

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_TH
from parce_screenshots.delete_any_popup import nuke_poll_overlay
from parce_screenshots.moduls.locators import TOP_ELEMENT_LOCATOR, POPULARS_LOCATOR
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def top_screen(page: Page, hotel_id, hotel_title=None):
    try:
        "https://tophotels.ru/en/hotel/al27382"
        url = BASE_URL_TH + "hotel/" + hotel_id
        await page.goto(url, timeout=0)

        await page.wait_for_selector(
            TOP_ELEMENT_LOCATOR, state="visible", timeout=30000
        )
        await nuke_poll_overlay(page)

        await page.wait_for_selector(POPULARS_LOCATOR, state="visible", timeout=30000)

        element = await page.query_selector(TOP_ELEMENT_LOCATOR)

        if element is None:
            raise PlaywrightError("TOP_ELEMENT_LOCATOR не найден")

        await element.screenshot(
            path=get_screenshot_path(hotel_id, hotel_title, "01_top_element.png")
        )
        element2 = await page.query_selector(POPULARS_LOCATOR)
        old_viewport = page.viewport_size
        await page.set_viewport_size({"width": 1550, "height": 1000})
        await element2.screenshot(
            path=get_screenshot_path(hotel_id, hotel_title, "02_populars_element.png")
        )
        await page.set_viewport_size(old_viewport)

    except Exception:
        logging.exception(f"[top_screen] Ошибка при выполнении {url}")
