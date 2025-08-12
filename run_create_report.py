import asyncio
import os
import shutil
from time import perf_counter

from config_app import SCREENSHOTS_DIR
from move_shot_to_word import create_formatted_doc
from parce_screenshots import run_create_report  # теперь он сам решит: concurrent/sequential
from utils import sleep_system

if __name__ == "__main__":
    t1 = perf_counter()
    asyncio.run(run_create_report())
    create_formatted_doc()
    print(f"\nElapsed: {perf_counter() - t1:.1f}s\n")
    if os.path.exists(SCREENSHOTS_DIR):
        shutil.rmtree(SCREENSHOTS_DIR)
    sleep_system()
