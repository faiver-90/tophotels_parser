import asyncio
import logging
from time import perf_counter

from config_app import SLEEP
from move_shot_to_word import create_formatted_doc
from parce_screenshots import run_create_report

from utils import sleep_system, delete_auth_state, delete_screenshots

if __name__ == "__main__":
    t1 = perf_counter()
    try:
        delete_screenshots()
        delete_auth_state()

        asyncio.run(run_create_report())
        create_formatted_doc(target_image_width_px=900)
        print(f"{'*' * 100} \nElapsed: {perf_counter() - t1:.1f}s\n {'*' * 100}")
        logging.info("*" * 100)
        if SLEEP:
            sleep_system()
    finally:
        delete_screenshots()
        # Удаляем, так как ТХ ПРО не видит регистрацию без проходки в регистрации
        try:
            delete_auth_state()
        except FileNotFoundError:
            pass
        except OSError as e:
            logging.warning("Не удалось удалить auth_state.json: %s", e)
