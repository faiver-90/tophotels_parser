import asyncio
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
        # 1) Строгая навигация + анти-попапы с ретраями + ожидание якорного селектора
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            expect_url=url,  # точное совпадение
            ready_selector=REVIEW_LOCATOR,  # якорный селектор раздела «Отзывы»
            timeout=45000,
            retries=2,
            retry_delay_ms=700,
            nuke_overlays=nuke_poll_overlay,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
        )

        # 2) Берём Locator и ждём видимость
        loc = page.locator(REVIEW_LOCATOR).first
        await loc.wait_for(state="visible", timeout=30000)

        # 3) Подстрахуемся от «видим, но 0x0»: ждём ненулевой bbox
        handle = await loc.element_handle()
        await page.wait_for_function(
            """el => {
                if (!el) return false;
                const r = el.getBoundingClientRect();
                return r.width > 2 && r.height > 2;
            }""",
            arg=handle,
            timeout=10000,
        )

        # 4) На всякий случай — скролл к блоку и короткая пауза
        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        await asyncio.sleep(0.2)

        # 5) Скрин
        await loc.screenshot(
            path=get_screenshot_path(hotel_id, hotel_title, "03_reviews.png")
        )

        # 6) Вернём счётчик отзывов (если нет — пустую строку)
        cnt_text = await page.locator(COUNT_REVIEW_LOCATOR).first.text_content()
        return (cnt_text or "").strip()

    except Exception:
        logging.exception(f"[review_screen] Ошибка при выполнении {url}")
        raise
