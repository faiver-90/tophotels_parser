import asyncio
import logging
import os
from pathlib import Path

from typing import List
from typing import Optional, Pattern
from playwright.async_api import Response

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import Error as PlaywrightError

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config_app import BASE_URL_PRO, BASE_URL_TH
from parce_screenshots_moduls.delete_any_popup import nuke_poll_overlay

from parce_screenshots_moduls.moduls.locators import TG_HIDE_LOCATOR, FLAG_LOCATOR


def load_hotel_ids(file_path: str) -> List[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip().lower().startswith("al") and line.strip()[2:].isdigit()
        ]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def get_title_hotel(page: Page, hotel_id):
    try:
        url = BASE_URL_TH + "hotel/" + hotel_id
        await goto_strict(page, url, nuke_overlays=nuke_poll_overlay, expect_url=url)
        #
        # await nuke_overlays(page)
        # await nuke_overlays_once(page)

        await page.wait_for_selector(
            "#container > div.topline > section.topline__info > a > h1",
            state="visible",
            timeout=30000,
        )
        element = await page.query_selector(
            "#container > div.topline > section.topline__info > a > h1"
        )
        if element is None:
            raise PlaywrightError("title_hotel не найден")
        title = await element.text_content()
        return title.strip()[:-2].strip()
    except Exception:
        logging.exception("[get_title_hotel] Ошибка при выполнении")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def hide_tg(page: Page):
    locator = page.locator(TG_HIDE_LOCATOR)

    try:
        if await locator.is_visible():
            await locator.click()
    except Exception as e:
        logging.exception(f"Клик на телеграм сломался, {e}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PlaywrightError),
)
async def set_language_en(page: Page):
    try:
        await page.goto(BASE_URL_PRO)

        await page.wait_for_selector(FLAG_LOCATOR, state="visible", timeout=30000)

        await page.click(FLAG_LOCATOR)

        await page.wait_for_selector(
            "#pp-lang:not(.hidden)", state="visible", timeout=30000
        )

        await page.wait_for_selector("#pp-lang:not(.hidden)", timeout=30000)
        await page.click('#pp-lang li[data-key="en"]')
        await asyncio.sleep(3)
    except Exception as e:
        logging.exception(f"[set_language_en] Ошибка при выборе языка: {e}")


# def all_folders_have_count_images(base_path: str, count_files_dir: int) -> bool:
#     for folder in os.listdir(base_path):
#         if folder == "None":
#             continue  # Пропустить папку с именем 'None'
#
#         folder_path = os.path.join(base_path, folder)
#         if not os.path.isdir(folder_path):
#             continue
#
#         images = [
#             f
#             for f in os.listdir(folder_path)
#             if f.lower().endswith((".png", ".jpg", ".jpeg"))
#         ]
#         if len(images) < count_files_dir:
#             print(f"🔁 Folder '{folder}' has only {len(images)} images.")
#             return False
#     return True


async def delete_locator(page: Page, locator: str) -> None:
    """
    Удаляет все элементы, найденные по локатору, из DOM.
    Если элемент не найден — ничего не делает.
    """
    elements = page.locator(locator)
    count = await elements.count()
    if count == 0:
        return  # ничего не найдено — выходим

    for i in range(count):
        await elements.nth(i).evaluate("el => el.remove()")


async def safe_full_page_screenshot(page: Page, save_path: str | Path) -> bool:
    """
    Делает скриншот полной страницы, обрабатывая исключения.

    Args:
        page: объект Page Playwright.
        save_path: путь, куда сохранить скриншот.

    Returns:
        bool: True, если скриншот создан, False — если произошла ошибка.
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        await page.screenshot(path=str(save_path), full_page=True)
        print(f"[OK] Полный скриншот сохранён: {save_path}")
        return True
    except PlaywrightTimeoutError as e:
        print(f"[ERROR] Таймаут при создании скриншота: {e}")
    except Exception as e:
        print(f"[ERROR] Не удалось сделать скриншот: {e}")
    return False


async def goto_strict(
    page: Page,
    url: str,
    *,
    wait_until: str = "networkidle",  # 'load' | 'domcontentloaded' | 'networkidle' | 'commit'
    expect_url: Optional[str | Pattern[str]] = None,  # строка или regex
    ready_selector: Optional[str] = None,  # селектор, который ДОЛЖЕН появиться
    timeout: int = 45000,
    retries: int = 2,  # сколько раз переехать при фейле
    retry_delay_ms: int = 500,  # пауза между попытками
    nuke_overlays: Optional[
        callable
    ] = None,  # функция анти-попапов: async (page) -> int
    overlays_kwargs: Optional[
        dict
    ] = None,  # kwargs для nuke_overlays (например, {'retries':3,'delay_ms':400})
) -> Response | None:
    """
    Надёжно переходит на URL и убеждается, что страница готова.

    Гарантии перед возвратом:
      - (опц.) URL соответствует expect_url (строка или regex),
      - (опц.) появился ready_selector (state='visible'),
      - (опц.) запущен анти-попап «пылесос» nuke_overlays.

    Бросает исключение, если после всех ретраев нужное состояние не достигнуто.
    """
    last_exc: Exception | None = None
    overlays_kwargs = overlays_kwargs or {}

    for attempt in range(retries + 1):
        try:
            # 1) Переход
            resp = await page.goto(url, wait_until=wait_until, timeout=timeout)

            # 2) Базовая проверка ответа (если есть Response)
            if resp and not resp.ok:
                raise RuntimeError(f"GET {url} -> HTTP {resp.status}")

            # 3) Дождаться полной готовности документа (подстраховка)
            await page.wait_for_function(
                "document.readyState === 'complete'", timeout=timeout
            )

            # 4) Анти-попапы (если передали функцию)
            if nuke_overlays:
                try:
                    await nuke_overlays(page, **overlays_kwargs)
                except Exception:
                    # не валим переход из-за чистки попапов
                    pass

            # 5) Проверка URL (если требуется)
            if expect_url is not None:
                await page.wait_for_url(expect_url, timeout=timeout)

            # 6) Ждём якорный селектор (если передан)
            if ready_selector:
                await page.wait_for_selector(
                    ready_selector, state="visible", timeout=timeout
                )

            # Всё ок — выходим
            return resp

        except Exception:
            if attempt < retries:
                # Мягкая задержка и повтор
                await asyncio.sleep(retry_delay_ms / 1000)
                continue
            # закончили попытки — пробрасываем
            raise
