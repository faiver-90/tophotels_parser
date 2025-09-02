import logging

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_TH
from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay
from parce_screenshots_moduls.moduls.locators import (
    TOP_ELEMENT_LOCATOR,
    POPULARS_LOCATOR,
    CITY_LOCATOR,
)
from parce_screenshots_moduls.utils import goto_strict
from utils import get_screenshot_path, normalize_text, save_to_jsonfile


async def save_city(page, hotel_id, hotel_title):
    await page.wait_for_selector(CITY_LOCATOR, state="visible", timeout=1000)
    element_city = await page.query_selector(CITY_LOCATOR)
    city_raw = (await element_city.text_content()) or ""
    city = normalize_text(city_raw).split("Hotels ")[-1]
    save_to_jsonfile(hotel_id, hotel_title, key="city", value=city)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def top_screen(page: Page, hotel_id, hotel_title=None):
    try:
        "https://tophotels.ru/en/hotel/al27382"
        url = BASE_URL_TH + "hotel/" + hotel_id
        await goto_strict(page, url, nuke_overlays=nuke_poll_overlay, expect_url=url)

        await page.wait_for_selector(
            TOP_ELEMENT_LOCATOR, state="visible", timeout=30000
        )
        await page.wait_for_selector(POPULARS_LOCATOR, state="visible", timeout=30000)

        await save_city(page, hotel_id, hotel_title)
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
