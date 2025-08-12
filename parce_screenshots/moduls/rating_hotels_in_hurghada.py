import logging

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from config_app import BASE_URL_PRO, RETRIES_FOR_DELETE_LOCATORS, DELAY_FOR_DELETE
from parce_screenshots.delete_any_popup import nuke_poll_overlay
from parce_screenshots.moduls.locators import (
    ALL_TABLE_RATING_OVEREVIEW_LOCATOR,
    RATING_HOTEL_IN_HURGHADA_LOCATOR,
    REVIEW_10_LOCATOR,
    REVIEW_50_LOCATOR,
)
from parce_screenshots.utils import goto_strict
from utils import get_screenshot_path, save_link


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def rating_hotels_in_hurghada(page, count_review, hotel_id, hotel_title=None):
    "https://tophotels.pro/hotel/al52488/new_stat/rating-hotels"
    url = BASE_URL_PRO + f"hotel/{hotel_id}" + "/new_stat/rating-hotels"

    try:
        await goto_strict(
            page,
            url,
            wait_until="networkidle",
            ready_selector=ALL_TABLE_RATING_OVEREVIEW_LOCATOR
            or RATING_HOTEL_IN_HURGHADA_LOCATOR,
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

        page_content = await page.content()
        if "There is no data for the hotel" in page_content:
            logging.warning(
                f"[{hotel_id}] Нет данных по отелю ({hotel_title}) — 'There is no data for the hotel'"
            )
            return
        if "To activate your business account, contact us" in page_content:
            try:
                await page.wait_for_selector(
                    ALL_TABLE_RATING_OVEREVIEW_LOCATOR, timeout=30000
                )
                element = await page.query_selector(ALL_TABLE_RATING_OVEREVIEW_LOCATOR)

                if element is None:
                    raise PlaywrightError(
                        "Элемент ALL_TABLE_RATING_OVEREVIEW_LOCATOR не найден"
                    )

                await element.screenshot(
                    path=get_screenshot_path(
                        hotel_id, hotel_title, "07_rating_in_hurghada.png"
                    )
                )
                return
            except PlaywrightError as e:
                logging.exception(
                    f"❌ Не удалось найти элемент активности для отеля {hotel_id}: {e}"
                )
                return

        if 10 < int(count_review.replace(" ", "")) < 50:
            await page.click(REVIEW_10_LOCATOR)
        else:
            await page.click(REVIEW_50_LOCATOR)

        await page.wait_for_selector(
            RATING_HOTEL_IN_HURGHADA_LOCATOR, state="visible", timeout=30000
        )

        await page.wait_for_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)
        element = await page.query_selector(RATING_HOTEL_IN_HURGHADA_LOCATOR)
        current_url = page.url
        save_link(hotel_id, hotel_title, "rating_url", current_url)

        if element:
            await element.screenshot(
                path=get_screenshot_path(
                    hotel_id, hotel_title, "07_rating_in_hurghada.png"
                )
            )
        else:
            print(
                f"[!] Таблица рейтинга не найдена у отеля {hotel_id} на странице {url}"
            )
    except Exception:
        element = await page.query_selector(ALL_TABLE_RATING_OVEREVIEW_LOCATOR)
        if element is None:
            raise PlaywrightError(
                f"[{hotel_id}] Элемент не найден даже в except — повторяем попытку"
            )
        await element.screenshot(
            path=get_screenshot_path(hotel_id, hotel_title, "07_rating_in_hurghada.png")
        )
        logging.exception(f"[rating_hotels_in_hurghada] Ошибка при выполнении {url}")
