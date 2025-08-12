import logging
import os

from PIL import Image
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_PRO, SCREENSHOTS_DIR
from parce_screenshots.moduls.locators import ACTIVITY_LOCATOR, TG_LOCATOR, FLAG_ON_TABLE_FOR_DELETE
from parce_screenshots.utils import delete_locator
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def last_activity(page: Page, hotel_id, hotel_title=None):
    try:
        url = BASE_URL_PRO + "hotel/" + hotel_id + '/activity/index'
        await page.goto(url, timeout=0)

        await page.wait_for_selector(ACTIVITY_LOCATOR, state="visible", timeout=30000)
        await delete_locator(page, TG_LOCATOR)
        await delete_locator(page, FLAG_ON_TABLE_FOR_DELETE)

        element = await page.query_selector(ACTIVITY_LOCATOR)
        if element is None:
            raise PlaywrightError("Элемент ACTIVITY_LOCATOR не найден")

        old_viewport = page.viewport_size
        await page.set_viewport_size({"width": 1400, "height": 1000})

        # screenshot_dir = os.path.join(SCREENSHOTS_DIR, hotel_title or "default")
        full_path = get_screenshot_path(
            hotel_id, hotel_title, "08_activity.png"
        )
        # os.makedirs(screenshot_dir, exist_ok=True)

        # full_path = os.path.join(screenshot_dir, "08_activity.png")

        # Сделать скриншот элемента
        await element.screenshot(path=full_path)

        # Обрезать нижнюю половину (оставить верхнюю)
        with Image.open(full_path) as img:
            width, height = img.size
            top_half = img.crop((0, 0, width, height // 2))  # (left, upper, right, lower)
            top_half.save(full_path)

        await page.set_viewport_size(old_viewport)

    except Exception as e:
        logging.exception(f"[last_activity] Ошибка при выполнении {url}")
