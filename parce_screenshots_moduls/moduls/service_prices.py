import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Page

from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay
from parce_screenshots_moduls.moduls.locators import (
    SERVICES_AND_PRICES_LOCATOR,
    FALLBACK_CONTAINER_SERVICE_PRICES
)
from parce_screenshots_moduls.utils import goto_strict, safe_full_page_screenshot
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type(Exception),
)
async def service_prices(page: Page, hotel_id, hotel_title=None):
    """
    https://tophotels.pro/al/<id>/stat/profile?group=day&vw=grouped
    Делаем переход максимально «строгим» и устойчивым к оверлеям/медленной сети.
    """
    url = f"{BASE_URL_PRO}al/{hotel_id[2:]}/stat/profile?group=week&vw=grouped"
    save_path = get_screenshot_path(hotel_id, hotel_title, "06_service_prices.png")

    try:
        # 1) Навигация + антипопапы + ожидание якорного селектора
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            expect_url=url,  # точное совпадение
            timeout=30000,
            retries=1,
            retry_delay_ms=0,
            nuke_overlays=nuke_poll_overlay,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
        )

        loc = page.locator(SERVICES_AND_PRICES_LOCATOR).first

        await loc.wait_for(state="visible", timeout=1000)
        old_vp = page.viewport_size or {"width": 1005, "height": 1000}
        try:
            await page.set_viewport_size(
                {"width": 1400, "height": old_vp.get("height", 1000)}
            )
            await loc.screenshot(path=save_path)
        finally:
            await page.set_viewport_size(old_vp)

    except Exception:
        try:
            cont = page.locator(FALLBACK_CONTAINER_SERVICE_PRICES).first
            if await cont.count():
                await cont.wait_for(state="visible", timeout=400)
                await cont.screenshot(path=save_path, timeout=600)
            else:
                await safe_full_page_screenshot(page, save_path)
        except Exception:
            logging.exception("[service_prices] Фолбэк-скрин не удался для %s", url)

        logging.exception("[service_prices] Ошибка при выполнении %s", url)
        raise
