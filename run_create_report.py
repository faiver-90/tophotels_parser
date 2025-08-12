import asyncio
import os
import shutil
from time import perf_counter

from config_app import SCREENSHOTS_DIR
from move_shot_to_word import create_formatted_doc
from parce_screenshots.parce_screenshots import run_create_report
from utils import sleep_system

if __name__ == "__main__":
    t1_start = perf_counter()
    asyncio.run(run_create_report())
    create_formatted_doc()
    t1_stop = perf_counter()
    print(
        "#" * 100,
        "\n",
        "Elapsed time during the whole program in seconds:",
        t1_stop - t1_start,
        "\n",
        "#" * 100,
    )
    if os.path.exists(SCREENSHOTS_DIR):
        shutil.rmtree(SCREENSHOTS_DIR)

    sleep_system()
