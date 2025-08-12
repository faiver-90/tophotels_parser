import asyncio


from concurrent_runner import hotels_needing_retry, run_concurrent, CONCURRENCY
from config_app import (
    HOTELS_IDS_FILE,
    SCREENSHOTS_DIR,
    MAX_ATTEMPTS_RUN,
    MAX_FIRST_RUN,
)

from parce_screenshots_moduls.utils import (
    load_hotel_ids,
    all_folders_have_count_images,
)


async def run_create_report():
    hotel_ids_all = load_hotel_ids(HOTELS_IDS_FILE)

    for attempt in range(1, MAX_ATTEMPTS_RUN + 1):
        print(f"\n🌀 Attempt {attempt} of {MAX_ATTEMPTS_RUN}")

        # На повторных попытках докидываем ТОЛЬКО те ID, где не хватает картинок
        ids_for_run = (
            hotel_ids_all
            if attempt == 1
            else hotels_needing_retry(SCREENSHOTS_DIR, hotel_ids_all, required_files=8)
        )
        if not ids_for_run:
            print("✅ Всё уже собрано.")
            break

        if CONCURRENCY > 1:
            await run_concurrent(ids_for_run)  # ПАРАЛЛЕЛЬНО

        if attempt >= MAX_FIRST_RUN and all_folders_have_count_images(
            SCREENSHOTS_DIR, 8
        ):
            # После нужного количества кругов — проверяем ещё раз
            left = hotels_needing_retry(
                SCREENSHOTS_DIR, hotel_ids_all, required_files=8
            )
            if not left:
                print("✅ All folders contain at least 8 images.")
                break
        else:
            print("⚠ Ещё один круг…")
            await asyncio.sleep(1)
    else:
        print("❌ Max attempts reached. Some folders still have less than 8 images.")
