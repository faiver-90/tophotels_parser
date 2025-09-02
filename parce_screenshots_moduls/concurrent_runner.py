# concurrent_runner.py
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Iterable

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from tqdm import tqdm

from config_app import (
    HOTELS_IDS_FILE,
    HEADLESS,
    RESOLUTION_W,
    RESOLUTION_H,
    ENABLED_SHOTS,
    CONCURRENCY,
    AUTH_STATE,
)
from auth_service import AuthService

from parce_screenshots_moduls.utils import (
    set_language_en,
    get_title_star_hotel,
)
from parce_screenshots_moduls.moduls.top_screen import top_screen
from parce_screenshots_moduls.moduls.review_screen import review_screen
from parce_screenshots_moduls.moduls.attendance import attendance
from parce_screenshots_moduls.moduls.service_prices import service_prices
from parce_screenshots_moduls.moduls.rating_hotels_in_hurghada import (
    rating_hotels_in_hurghada,
)
from parce_screenshots_moduls.moduls.last_activity import last_activity

from utils import safe_step, save_to_jsonfile, load_hotel_ids  # твоя обёртка


async def login_once_and_save_state(browser: Browser) -> None:
    """Одна авторизация → сохраняем storage_state в файл для последующего reuse."""
    ctx = await browser.new_context()
    page = await ctx.new_page()
    try:
        await set_language_en(page)
        await AuthService(page).login()
        await ctx.storage_state(path=str(AUTH_STATE))
        logging.info("🔐 storage_state сохранён в %s", AUTH_STATE)
    finally:
        await ctx.close()


async def make_context(browser: Browser) -> BrowserContext:
    """Создаём контекст с загруженным storage_state (без повторного логина)."""
    if not AUTH_STATE.exists():
        await login_once_and_save_state(browser)
    return await browser.new_context(
        storage_state=str(AUTH_STATE),
        locale="en-US",
        viewport={"width": RESOLUTION_W, "height": RESOLUTION_H},
    )


async def process_hotel(page: Page, hotel_id: str) -> None:
    """Полный пайплайн по одному отелю на своей странице."""
    title, star = await safe_step(get_title_star_hotel, page, hotel_id)
    save_to_jsonfile(hotel_id, title, key="star", value=star)
    if title is None:
        logging.warning(
            "⚠ Не удалось получить title для %s, пробуем ещё раз...", hotel_id
        )
        title = await safe_step(get_title_star_hotel, page, hotel_id)

    await safe_step(top_screen, page, hotel_id, title)
    count_review = await safe_step(review_screen, page, hotel_id, title)
    await safe_step(attendance, page, hotel_id, title)
    await safe_step(service_prices, page, hotel_id, title)
    await safe_step(rating_hotels_in_hurghada, page, count_review, hotel_id, title)
    await safe_step(last_activity, page, hotel_id, title)

    logging.info("✅ Готово: %s (%s)", hotel_id, title)


async def worker(
    name: str, browser: Browser, queue: asyncio.Queue[str], pbar: tqdm
) -> None:
    """Воркер: свой контекст и одна страница, берёт ID из очереди."""
    ctx = await make_context(browser)
    page = await ctx.new_page()
    try:
        while True:
            hotel_id = await queue.get()
            try:
                logging.info("[%s] ▶ %s", name, hotel_id)
                await process_hotel(page, hotel_id)
            except Exception:
                logging.exception("[%s] Ошибка при обработке %s", name, hotel_id)
            finally:
                pbar.update(1)
                queue.task_done()
    except asyncio.CancelledError:
        pass
    finally:
        await page.close()
        await ctx.close()


def _dedupe(seq: Iterable[str]) -> list[str]:
    """Убираем повторы, сохраняя порядок."""
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _hotel_folder_matches(hotel_id: str, folder_name: str) -> bool:
    # Папки у тебя вида "al233_Jaz Fayrouz" — сверяем префикс до подчёркивания
    return folder_name.startswith(f"{hotel_id}_")


REQUIRED_EXT = {".png", ".jpg", ".jpeg"}


def hotels_needing_retry(screens_dir: Path, hotel_ids: list[str]) -> list[str]:
    need = []
    existing = [p.name for p in screens_dir.glob("*") if p.is_dir()]
    for hid in hotel_ids:
        fold = next((f for f in existing if _hotel_folder_matches(hid, f)), None)
        if not fold:
            need.append(hid)
            continue
        files = {
            p.name
            for p in (screens_dir / fold).iterdir()
            if p.suffix.lower() in REQUIRED_EXT
        }
        # проверяем именно нужные имена
        missing = [name for name in ENABLED_SHOTS if name not in files]
        if missing:
            need.append(hid)
    return need


async def run_concurrent(hotel_ids: Optional[list[str]] = None) -> None:
    """
    Параллельная обработка.
    Если hotel_ids не переданы — загружаем из файла.
    """
    hotel_ids = _dedupe(hotel_ids or load_hotel_ids(HOTELS_IDS_FILE))
    if not hotel_ids:
        logging.error("Файл с ID пуст или некорректен.")
        return
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS)

            queue: asyncio.Queue[str] = asyncio.Queue()
            for hid in hotel_ids:
                queue.put_nowait(hid)

            pbar = tqdm(total=len(hotel_ids), desc="Обработка отелей", unit="отель")

            n_workers = max(1, CONCURRENCY)
            tasks = [
                asyncio.create_task(worker(f"W{i + 1}", browser, queue, pbar))
                for i in range(n_workers)
            ]

            await queue.join()
            pbar.close()

            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logging.exception(f"Ошибка при инициализации браузера: {e}")
    finally:
        await browser.close()
