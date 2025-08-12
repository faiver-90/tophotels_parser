import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError, Page

from config_app import BASE_URL_TH, DELAY_FOR_DELETE, RETRIES_FOR_DELETE_LOCATORS
from parce_screenshots.delete_any_popup import nuke_poll_overlay
from parce_screenshots.moduls.locators import REVIEW_LOCATOR, COUNT_REVIEW_LOCATOR
from parce_screenshots.utils import goto_strict
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def review_screen(page: Page, hotel_id, hotel_title=None):
    """
    Пример URL: https://tophotels.ru/en/hotel/al27382/reviews
    Переход делаем «строгим», чистим попапы, ждём видимость и ненулевой размер блока.
    """
    url = f"{BASE_URL_TH}hotel/{hotel_id}/reviews"
    try:
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            expect_url=url,
            timeout=45000,
            retries=1,
            retry_delay_ms=500,
            nuke_overlays=nuke_poll_overlay,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
        )

        needle = "Write a review and you will forever be the pioneer of this hotel, just like Columbus of America!"

        try:
            await page.get_by_text(needle, exact=False).first.wait_for(timeout=500)
            text_found = True
        except TimeoutError:
            text_found = False

        if text_found:
            await page.locator("#container").screenshot(
                path=get_screenshot_path(hotel_id, hotel_title, "03_reviews.png")
            )
            return ""
        else:
            loc = page.locator(REVIEW_LOCATOR).first
            await loc.wait_for(state="visible", timeout=500)

            await loc.screenshot(
                path=get_screenshot_path(hotel_id, hotel_title, "03_reviews.png")
            )

        cnt_text = await page.locator(COUNT_REVIEW_LOCATOR).first.text_content()
        return (cnt_text or "").strip()

    except Exception:
        logging.exception(f"[review_screen] Ошибка при выполнении {url}")
        raise
