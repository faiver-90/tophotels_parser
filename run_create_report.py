import asyncio
import logging
import os
import shutil
from time import perf_counter

from config_app import SLEEP, SCREENSHOTS_DIR, AUTH_STATE
from move_shot_to_word import create_formatted_doc
from parce_screenshots import run_create_report


from utils import sleep_system

if __name__ == "__main__":
    t1 = perf_counter()
    try:
        asyncio.run(run_create_report())
        create_formatted_doc(target_image_width_px=1200)
        print(f"{'*' * 100} \nElapsed: {perf_counter() - t1:.1f}s\n {'*' * 100}")
        logging.info("*" * 100)
        if SLEEP:
            sleep_system()
    finally:
        if os.path.exists(SCREENSHOTS_DIR):
            shutil.rmtree(SCREENSHOTS_DIR)
        # Удаляем, так как ТХ ПРО не видит регистрацию без проходки в регистрации
        try:
            os.remove(AUTH_STATE)
        except FileNotFoundError:
            pass
        except OSError as e:
            logging.warning("Не удалось удалить auth_state.json: %s", e)
