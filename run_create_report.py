import asyncio

from move_shot_to_word import create_formatted_doc
from parce_screenshots.parce_screenshots import run_create_report

if __name__ == "__main__":
    asyncio.run(run_create_report())
    create_formatted_doc()
