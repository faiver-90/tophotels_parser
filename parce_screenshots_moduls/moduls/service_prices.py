import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Page
from pathlib import Path
import tempfile
from PIL import Image
from playwright.async_api import TimeoutError as PWTimeoutError

from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay
from parce_screenshots_moduls.moduls.locators import FALLBACK_CONTAINER_SERVICE_PRICES

from parce_screenshots_moduls.utils import goto_strict, safe_full_page_screenshot
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(Exception),
)
async def service_prices(page: Page, hotel_id, hotel_title=None):
    """
    Скрин exactly: thead + первые две строки tbody из секции 'SERVICES AND PRICES'.
    """
    url = f"{BASE_URL_PRO}al/{hotel_id[2:]}/stat/profile?group=week&vw=grouped"
    save_path = get_screenshot_path(hotel_id, hotel_title, "06_service_prices.png")

    try:
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            expect_url=url,
            timeout=45000,
            retries=1,
            retry_delay_ms=0,
            nuke_overlays=nuke_poll_overlay,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
        )

        PAD_X, PAD_Y = 8, 8

        # 0) Найти именно НУЖНУЮ таблицу без заголовка h2
        # Вариант А: XPath по содержимому второй строки "Tour search"
        xpath_srv_table = (
            "xpath=(//table[contains(@class,'hotel-stat-section')]"
            "[tbody/tr[1]/td[1][contains(translate(normalize-space(.),"
            " 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'IN TOTAL')]"
            " and tbody/tr[2]/td[1][contains(translate(normalize-space(.),"
            " 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'TOUR SEARCH')]])[1]"
        )

        table = page.locator(xpath_srv_table)
        try:
            await table.wait_for(state="visible", timeout=7000)
        except PWTimeoutError:
            # Вариант B (локализация строки «ПОИСК ТУРА», если такая бывает)
            xpath_srv_table = (
                "xpath=(//table[contains(@class,'hotel-stat-section')]"
                "[tbody/tr[2]/td[1][contains(translate(normalize-space(.),"
                " 'абвгдежзийклмнопрстуфхцчшщьыъэюя',"
                " 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ'),'ПОИСК')"
                " or contains(translate(normalize-space(.),"
                " 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'TOUR SEARCH')]])[1]"
            )
            table = page.locator(xpath_srv_table)
            await table.wait_for(state="visible", timeout=7000)

        # 1) Сброс горизонтального скролла на всякий случай
        try:
            await table.evaluate("""(el)=>{
                const p = el.parentElement;
                if(p && typeof p.scrollLeft==='number') p.scrollLeft = 0;
                if(typeof el.scrollLeft==='number') el.scrollLeft = 0;
            }""")
        except Exception:
            pass

        # 2) Снимем САМУ таблицу целиком (element.screenshot не требует «влезания» в вьюпорт)
        tmp_png = Path(tempfile.gettempdir()) / f"_srv_prices_{hotel_id}.png"
        await table.screenshot(path=str(tmp_png), animations="disabled")

        # 3) Получим метрики thead и первых двух строк относительно начала TABLE
        metrics = await table.evaluate(
            """(tbl)=>{
                const thead = tbl.querySelector('thead');
                const r1 = tbl.querySelector('tbody tr:nth-child(1)');
                const r2 = tbl.querySelector('tbody tr:nth-child(2)');
                if(!thead || !r1 || !r2) return null;

                const t = tbl.getBoundingClientRect();
                const part = (el)=>{ const r = el.getBoundingClientRect();
                    return {top:Math.round(r.top - t.top),
                            left:Math.round(r.left - t.left),
                            width:Math.round(r.width),
                            height:Math.round(r.height)};
                };
                return {thead:part(thead), row1:part(r1), row2:part(r2)};
            }"""
        )
        if not metrics:
            raise RuntimeError("SERVICES AND PRICES: не получили метрики thead/rows")

        # 4) Считаем рамку кропа: thead + первые 2 строки
        left = (
                min(
                    metrics["thead"]["left"],
                    metrics["row1"]["left"],
                    metrics["row2"]["left"],
                )
                - PAD_X
        )
        right = (
                max(
                    metrics["thead"]["left"] + metrics["thead"]["width"],
                    metrics["row1"]["left"] + metrics["row1"]["width"],
                    metrics["row2"]["left"] + metrics["row2"]["width"],
                )
                + PAD_X
        )
        top = min(metrics["thead"]["top"], metrics["row1"]["top"]) - PAD_Y
        bottom = max(
            metrics["row2"]["top"] + metrics["row2"]["height"],
            metrics["row1"]["top"] + metrics["row1"]["height"],
        )

        # 5) Кроп и сохранение к финальному пути
        with Image.open(tmp_png) as im:
            W, H = im.size
            box = (max(0, left), max(0, top), min(W, right), min(H, bottom))
            im.crop(box).save(save_path)

    except Exception:
        # Резерв: контейнер/фуллпейдж (из твоего исходника)
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

#
#
# import logging
# from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
# from playwright.async_api import Page
#
# from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
# from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay
# from parce_screenshots_moduls.moduls.locators import (
#     SERVICES_AND_PRICES_LOCATOR,
#     FALLBACK_CONTAINER_SERVICE_PRICES,
# )
# from parce_screenshots_moduls.utils import goto_strict, safe_full_page_screenshot
# from utils import get_screenshot_path
#
#
# @retry(
#     stop=stop_after_attempt(2),
#     wait=wait_fixed(0.5),
#     retry=retry_if_exception_type(Exception),
# )
# async def service_prices(page: Page, hotel_id, hotel_title=None):
#     """
#     https://tophotels.pro/al/<id>/stat/profile?group=day&vw=grouped
#     Делаем переход максимально «строгим» и устойчивым к оверлеям/медленной сети.
#     """
#     url = f"{BASE_URL_PRO}al/{hotel_id[2:]}/stat/profile?group=week&vw=grouped"
#     save_path = get_screenshot_path(hotel_id, hotel_title, "06_service_prices.png")
#
#     try:
#         # 1) Навигация + антипопапы + ожидание якорного селектора
#         await goto_strict(
#             page,
#             url,
#             wait_until="networkidle",
#             expect_url=url,  # точное совпадение
#             timeout=30000,
#             retries=1,
#             retry_delay_ms=0,
#             nuke_overlays=nuke_poll_overlay,
#             overlays_kwargs={
#                 "retries": RETRIES_FOR_DELETE_LOCATORS,
#                 "delay_ms": DELAY_FOR_DELETE,
#             },
#         )
#
#         loc = page.locator(SERVICES_AND_PRICES_LOCATOR).first
#
#         await loc.wait_for(state="visible", timeout=1000)
#         old_vp = page.viewport_size or {"width": 1005, "height": 1000}
#         try:
#             await page.set_viewport_size(
#                 {"width": 1400, "height": old_vp.get("height", 1000)}
#             )
#             await loc.screenshot(path=save_path)
#         finally:
#             await page.set_viewport_size(old_vp)
#
#     except Exception:
#         try:
#             cont = page.locator(FALLBACK_CONTAINER_SERVICE_PRICES).first
#             if await cont.count():
#                 await cont.wait_for(state="visible", timeout=400)
#                 await cont.screenshot(path=save_path, timeout=600)
#             else:
#                 await safe_full_page_screenshot(page, save_path)
#         except Exception:
#             logging.exception("[service_prices] Фолбэк-скрин не удался для %s", url)
#
#         logging.exception("[service_prices] Ошибка при выполнении %s", url)
#         raise
