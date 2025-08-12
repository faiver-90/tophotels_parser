import asyncio
import logging

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_PRO, SCREENSHOTS_DIR
from parce_screenshots.moduls.locators import (
    ATTENDANCE_LOCATOR,
    INCORRECT_DATA_SELECTOR,
    ACTIVATION_REQUIRES_SELECTOR,
)
from utils import get_screenshot_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def attendance(page: Page, hotel_id, hotel_title=None):
    url = (
        BASE_URL_PRO
        + "hotel/"
        + hotel_id
        + "/new_stat/attendance?filter%5Bperiod%5D=30"
    )
    attempts = 5

    try:
        for attempt in range(attempts):
            await page.goto(url, timeout=0)

            # Ждём основной контент
            await page.wait_for_selector(
                ATTENDANCE_LOCATOR, state="visible", timeout=30000
            )

            # 1Проверка: "неверные данные"
            if await page.is_visible(INCORRECT_DATA_SELECTOR):
                text = await page.inner_text(INCORRECT_DATA_SELECTOR)
                if "At the moment, the service may show incorrect data" in text:
                    logging.warning(
                        f"[attendance] Предупреждение о данных на {hotel_id}. Попытка {attempt + 1} из {attempts}"
                    )
                    await asyncio.sleep(2)
                    continue  # пробуем ещё раз

            # Проверка: "требуется активация"
            page_content = await page.content()
            if (
                "Attention! For this report you need an additional activation."
                in page_content
            ):
                logging.warning(
                    f"[attendance] Требуется активация отчёта для {hotel_id}"
                )
                try:
                    element = await page.query_selector(ACTIVATION_REQUIRES_SELECTOR)
                    if element:
                        path = get_screenshot_path(
                            hotel_id, hotel_title, "04_attendance.png"
                        )
                        await element.screenshot(path=path)
                        logging.info(
                            f"[attendance] Скриншот таблицы при требуемой активации сохранён: {path}"
                        )
                    else:
                        logging.warning(
                            f"[attendance] Таблица при активации не найдена на {hotel_id}"
                        )
                except Exception as e:
                    logging.exception(
                        f"[attendance] Ошибка при скриншоте таблицы активации: {e}"
                    )
                return

            # Всё нормально — делаем обычный скриншот
            element = await page.query_selector(ATTENDANCE_LOCATOR)
            await element.screenshot(
                path=get_screenshot_path(hotel_id, hotel_title, "04_attendance.png")
            )
            return

        # Ошибка "неверные данные" осталась после всех попыток
        if await page.is_visible(INCORRECT_DATA_SELECTOR):
            error_element = await page.query_selector(INCORRECT_DATA_SELECTOR)
            await error_element.screenshot(
                path=get_screenshot_path(hotel_id, hotel_title, "04_attendance.png")
            )
            logging.warning(
                f"[attendance] После {attempts} попыток ошибка осталась. Сделан скрин ошибки."
            )
    except Exception as e:
        logging.exception(f"[attendance] Ошибка при выполнении {url}")
