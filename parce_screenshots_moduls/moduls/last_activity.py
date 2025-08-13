import logging

from PIL import Image
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page
from parce_screenshots_moduls.utils import goto_strict

from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay
from parce_screenshots_moduls.moduls.locators import (
    ACTIVITY_TABLE_LOCATOR,
    ROW_ACTIVITY_TABLE_LOCATOR,
)
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def last_activity(page: Page, hotel_id, hotel_title=None):
    try:
        url = BASE_URL_PRO + "hotel/" + hotel_id + "/activity/index"
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            ready_selector=ACTIVITY_TABLE_LOCATOR,
            timeout=45000,
            retries=2,
            nuke_overlays=nuke_poll_overlay,
            retry_delay_ms=700,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
            expect_url=url,
        )
        await page.wait_for_selector(
            ACTIVITY_TABLE_LOCATOR, state="visible", timeout=30000
        )

        element = await page.query_selector(ACTIVITY_TABLE_LOCATOR)
        if element is None:
            raise PlaywrightError("Элемент ACTIVITY_LOCATOR не найден")

        old_viewport = page.viewport_size
        await page.set_viewport_size({"width": 1400, "height": 1000})

        full_path = get_screenshot_path(hotel_id, hotel_title, "08_activity.png")
        # Сделать скриншот элемента
        await element.screenshot(path=full_path)

        # Определить количество строк в таблице
        row_count = await page.locator(ROW_ACTIVITY_TABLE_LOCATOR).count()
        # Если строк больше двух — обрезаем
        if row_count > 24 * 2:
            with Image.open(full_path) as img:
                width, height = img.size
                top_half = img.crop(
                    (0, 0, width, height // 2)
                )  # Оставляем верхнюю половину
                top_half.save(full_path)

        await page.set_viewport_size(old_viewport)

    except Exception:
        logging.exception(f"[last_activity] Ошибка при выполнении {url}")
