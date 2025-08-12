import asyncio
import os
import shutil

from config_app import SCREENSHOTS_DIR
from move_shot_to_word import create_formatted_doc
from parce_screenshots.parce_screenshots import run_create_report

if __name__ == "__main__":
    asyncio.run(run_create_report())
    create_formatted_doc()

    # if os.path.exists(SCREENSHOTS_DIR):
    #     shutil.rmtree(SCREENSHOTS_DIR)
