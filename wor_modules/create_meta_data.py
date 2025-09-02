from config_app import BASE_URL_TH, CURRENT_YEAR, CURRENT_MONTH
from utils import load_links
from wor_modules.docs_helpers import build_reports_dir, build_mapping


def create_meta_data(hotel_id, title_hotel):
    json_file = load_links(hotel_id, title_hotel)
    city = json_file.get("city", "City")
    reports_dir = build_reports_dir(CURRENT_YEAR, CURRENT_MONTH, city)
    star = json_file.get("star", "*")
    rating_url = json_file.get("rating_url")
    url_hotel = f"{BASE_URL_TH}hotel/{hotel_id}"
    mapping_paragraph = build_mapping(
        hotel_id, rating_url=rating_url, city=city, star=star
    )
    return url_hotel, mapping_paragraph, reports_dir