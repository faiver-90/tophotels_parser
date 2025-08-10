import logging
import os

from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page

from config_app import BASE_URL_PRO, SCREENSHOTS_DIR


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError)
)
async def dynamic_rating(page: Page, hotel_id, hotel_title=None):
    current_year = datetime.now().year

    try:
        url = BASE_URL_PRO + 'hotel/' + f"{hotel_id}/new_stat/dynamics#month"
        await page.goto(url)
        await page.wait_for_selector('#panel-month .bth__tbl', state="visible", timeout=10000)
        await page.wait_for_timeout(1000)

        # Поиск заголовка нужного года
        header_locator = page.locator(
            f"xpath=//div[@id='panel-month']//div[contains(@class, 'bth__row') and contains(., 'In total: {current_year}')]"
        )

        try:
            await header_locator.wait_for(timeout=5000)
        except:
            print(f"❌ Не найден блок 'In total: {current_year}' для отеля {hotel_id}")
            return

        header_index = await header_locator.evaluate(
            "node => Array.from(node.parentNode.children).indexOf(node)"
        )

        # Сбор всех строк таблицы
        all_rows = page.locator("#panel-month .bth__row")
        count = await all_rows.count()

        indexes = []
        for i in range(header_index + 1, count):
            row = all_rows.nth(i)
            html = await row.evaluate("e => e.outerHTML")
            if 'In total:' in html:
                break
            indexes.append(i)

        elements_to_shot = [all_rows.nth(i) for i in [header_index] + indexes]
        boxes = []

        for el in elements_to_shot:
            try:
                await el.scroll_into_view_if_needed(timeout=2000)
                box = await el.bounding_box()
                if box:
                    boxes.append(box)
            except Exception as e:
                print(f"⚠️ Пропущен элемент [dynamic_rating]: {e}")

        if not boxes:
            print(f"❌ Не найдены строки для {current_year} в отеле {hotel_id}")
            return

        # Область скриншота
        min_x = min(box['x'] for box in boxes)
        min_y = min(box['y'] for box in boxes)
        max_x = max(box['x'] + box['width'] for box in boxes)
        max_y = max(box['y'] + box['height'] for box in boxes)

        clip_area = {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }

        if clip_area["width"] <= 0 or clip_area["height"] <= 0:
            print(f"❌ Некорректная область скрина: {clip_area}")
            return

        os.makedirs(f"{SCREENSHOTS_DIR}/{hotel_title or 'default'}", exist_ok=True)
        path = f'{SCREENSHOTS_DIR}/{hotel_title or "default"}/05_dynamic_rating.png'

        await page.screenshot(path=path, clip=clip_area)
    except Exception as e:
        logging.exception(f"[dynamic_rating] Ошибка при обработке отеля {hotel_id}: {e}, {url}")
