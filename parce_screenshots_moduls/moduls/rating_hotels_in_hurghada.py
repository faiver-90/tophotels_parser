import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError, TimeoutError
from playwright.async_api import Page

from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay
from parce_screenshots_moduls.moduls.locators import (
    ALL_TABLE_RATING_OVEREVIEW_LOCATOR,
    RATING_HOTEL_IN_HURGHADA_LOCATOR,
    CITY_NAME_AND_STAR_LOCATOR,
    REVIEW_10_LOCATOR,
    REVIEW_50_LOCATOR, NO_DATA_SELECTOR,
)
from parce_screenshots_moduls.utils import goto_strict
from utils import get_screenshot_path, save_to_jsonfile, normalize_text


async def _safe_element_screenshot(page: Page, selector: str, path: str) -> None:
    """Скрин элемента, а если его нет — скрин всей страницы."""
    try:
        el = await page.query_selector(selector)
        if el:
            await el.screenshot(path=path)
        else:
            await page.screenshot(path=path, full_page=True)
    except Exception:
        # На крайний случай — скрин всей страницы
        try:
            await page.screenshot(path=path, full_page=True)
        except Exception:
            logging.exception("Не удалось сделать скриншот ни элемента, ни страницы")


async def error_handlers(page: Page, page_content: str, hotel_id: str, hotel_title: str) -> bool:
    """
    Возвращает True, если ситуация терминальная и дальше идти не нужно.
    Делает скрины и логирует.
    """
    # 1) Нет данных по отелю
    if "There is no data for the hotel" in page_content:
        logging.warning(f"[{hotel_id}] Нет данных по отелю ({hotel_title}) — 'There is no data for the hotel'")
        # Скриним блок, который точно есть, или всю страницу
        await _safe_element_screenshot(
            page,
            selector=NO_DATA_SELECTOR,
            path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada.png"),
        )
        # Можно сохранить маркёр в JSON для последующей логики
        save_to_jsonfile(hotel_id, hotel_title, key="rating_status", value="no_data")
        return True  # <- ВАЖНО: больше ничего не делаем

    # 2) Аккаунт не активирован
    if "To activate your business account, contact us" in page_content:
        logging.warning(f"[{hotel_id}] Бизнес-аккаунт не активирован ({hotel_title})")
        await _safe_element_screenshot(
            page,
            selector=ALL_TABLE_RATING_OVEREVIEW_LOCATOR,  # если нет — упадём на фулл-скрин
            path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada.png"),
        )
        save_to_jsonfile(hotel_id, hotel_title, key="rating_status", value="account_inactive")
        return True

    return False


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((PlaywrightError, TimeoutError)),
)
async def rating_hotels_in_hurghada(page: Page, count_review: str, hotel_id: str, hotel_title: str | None = None):
    url = BASE_URL_PRO + f"hotel/{hotel_id}/new_stat/rating-hotels"

    try:
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            timeout=30000,
            retries=0,
            nuke_overlays=nuke_poll_overlay,
            retry_delay_ms=200,
            overlays_kwargs={
                "retries": RETRIES_FOR_DELETE_LOCATORS,
                "delay_ms": DELAY_FOR_DELETE,
            },
            expect_url=url,
        )

        page_content = await page.content()

        # Если терминальная ветка — выходим сразу
        if await error_handlers(page, page_content, hotel_id, hotel_title):
            return

        # --- обычный сценарий ---
        # Город и звезды: селектор есть только на «полной» странице
        await page.wait_for_selector(CITY_NAME_AND_STAR_LOCATOR, state="visible", timeout=1000)
        element_city = await page.query_selector(CITY_NAME_AND_STAR_LOCATOR)
        city_raw = (await element_city.text_content()) or ""
        # Разбор без падений на коротких строках
        parts = [p.strip() for p in city_raw.split("/") if p.strip()]
        last_part = parts[-1] if parts else city_raw
        words = last_part.split()
        city = normalize_text(" ".join(words[-2:]) if len(words) >= 2 else last_part)[:-2].strip()
        star = normalize_text(" ".join(words[-2:]) if len(words) >= 2 else last_part)[-2:].strip()
        save_to_jsonfile(hotel_id, hotel_title, key="city", value=city)
        save_to_jsonfile(hotel_id, hotel_title, key="star", value=star)

        # Переключатель по количеству отзывов
        reviews_num = int(count_review.replace(" ", "") or "0")
        await page.click(REVIEW_10_LOCATOR if 10 < reviews_num < 50 else REVIEW_50_LOCATOR)

        await page.wait_for_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR, state="visible", timeout=3000)
        element = await page.query_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)

        current_url = page.url
        save_to_jsonfile(hotel_id, hotel_title, "rating_url", current_url)

        if element:
            await element.screenshot(
                path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada.png")
            )
        else:
            logging.warning(f"[{hotel_id}] Таблица рейтинга не найдена на {url}")

    except TimeoutError:
        # Таймауты часто не лечатся бесконечными ретраями — делаем один скрин и выходим
        logging.exception(f"[rating_hotels_in_hurghada] Timeout on {url}")
        await _safe_element_screenshot(
            page,
            selector=ALL_TABLE_RATING_OVEREVIEW_LOCATOR,
            path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada.png"),
        )
        # Не поднимаем PlaywrightError — чтобы не зациклиться
    except PlaywrightError:
        # Одна диагностическая попытка: скрин «основного» блока
        logging.exception(f"[rating_hotels_in_hurghada] PlaywrightError on {url}")
        await _safe_element_screenshot(
            page,
            selector=ALL_TABLE_RATING_OVEREVIEW_LOCATOR,
            path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada_error.png"),
        )
        # Исключение перехвачено — наружу не кидаем, чтобы прекратить ретраи
    except Exception:
        # Любая прочая ошибка — тоже фиксируем и выходим
        logging.exception(f"[rating_hotels_in_hurghada] Unexpected error on {url}")
        await _safe_element_screenshot(
            page,
            selector=ALL_TABLE_RATING_OVEREVIEW_LOCATOR,
            path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada_unexpected.png"),
        )
