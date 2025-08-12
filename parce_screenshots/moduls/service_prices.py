import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError, Page

from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
from parce_screenshots.delete_any_popup import nuke_poll_overlay
from parce_screenshots.moduls.locators import SERVICES_AND_PRICES_LOCATOR
from parce_screenshots.utils import goto_strict
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def service_prices(page: Page, hotel_id, hotel_title=None):
    """
    https://tophotels.pro/al/<id>/stat/profile?group=day&vw=grouped
    Делаем переход максимально «строгим» и устойчивым к оверлеям/медленной сети.
    """
    url = f"{BASE_URL_PRO}al/{hotel_id[2:]}/stat/profile?group=day&vw=grouped"
    try:
        # 1) Навигация + антипопапы + ожидание якорного селектора
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            expect_url=url,  # точное совпадение
            ready_selector=SERVICES_AND_PRICES_LOCATOR,  # якорный селектор страницы
            timeout=45000,
            retries=2,
            retry_delay_ms=700,
            nuke_overlays=nuke_poll_overlay,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
        )

        # 2) Берём Locator (надёжнее ElementHandle), ждём видимости и ненулевого размера
        loc = page.locator(SERVICES_AND_PRICES_LOCATOR).first

        # дождаться attach + видимости
        await loc.wait_for(state="visible", timeout=30000)

        # на некоторых страницах элемент видим, но 0x0 — ждём ненулевой bounding box
        await page.wait_for_function(
            """el => {
                if (!el) return false;
                const r = el.getBoundingClientRect();
                return r.width > 2 && r.height > 2;
            }""",
            arg=await loc.element_handle(),
            timeout=10000,
        )

        # 3) на всякий случай скроллим (если вне вьюпорта), это не навредит
        try:
            await loc.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass

        # 4) иногда после чистки попапов ещё что-то дорисовывается — подстрахуемся
        await asyncio.sleep(200 / 1000)

        # 5) снимок: аккуратно меняем viewport
        old_vp = page.viewport_size or {"width": 1005, "height": 1000}
        try:
            await page.set_viewport_size(
                {"width": 1400, "height": old_vp.get("height", 1000)}
            )
            # можно скринить прям из локатора — меньше возни с ElementHandle
            await loc.screenshot(
                path=get_screenshot_path(hotel_id, hotel_title, "06_service_prices.png")
            )
        finally:
            # всегда возвращаем исходный viewport
            await page.set_viewport_size(old_vp)

    except Exception:
        logging.exception(f"[service_prices] Ошибка при выполнении {url}")
        raise
