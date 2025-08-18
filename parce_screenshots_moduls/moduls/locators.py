TITLE_HOTEL_LOCATOR = "#container > div.topline > section.topline__info > a > h1"
TOP_ELEMENT_LOCATOR = "#container > div.topline"
POPULARS_LOCATOR = "#container > div.js-start-fixed-btn.grid > article > div.card-hotel-wrap > section.stata-bubble.stata-bubble--fz13-laptop.no-scrollbar"
REVIEW_LOCATOR = (
    "#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section"
)
ATTENDANCE_LOCATOR = "#pg-container-stat > div:nth-child(1)"
ACTIVITY_TABLE_LOCATOR = "#tab-pjax-index > div.js-bth__tbl.js-act-long-view"
ROW_ACTIVITY_TABLE_LOCATOR = "#events-list-table > tr"
RATING_HOTEL_IN_HURGHADA_LOCATOR = "//*[@id='tab-pjax-index']/div[4]"
NAME_RATING_TABLE_LOCATOR = '//*[@id="rty"]'
NO_DATA_SELECTOR = 'body > div.page > div:nth-child(6) > div.w100p.content-booking'

SERVICES_AND_PRICES_LOCATOR = "#hotelProfileApp > table:nth-child(5)"
TG_HIDE_LOCATOR = "section.js-block.thpro-tg-infoblock > i"
ALL_TABLE_RATING_OVEREVIEW_LOCATOR = "#tab-pjax-index > div > div.js-act-long-view"
FLAG_LOCATOR = "div > div > button > i"
EN_LANG_BUTTON_LOCATOR = '#pp-lang li[data-key="en"]'
COUNT_REVIEW_LOCATOR = (
    "#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section > "
    "div.card-hotel-rating-list > ul:nth-child(4) > li:nth-child(1) > b"
)
INCORRECT_DATA_SELECTOR = (
    "#cstm-filter-frm > article > div.js-filter-info.filter-new__info-wrap"
)
ACTIVATION_REQUIRES_SELECTOR = "#pg-container-stat > div > table"
REVIEW_10_LOCATOR = (
    "//*[@id='tab-pjax-index']/div/div[2]/div[6]/table/tbody/tr[2]/td[2]/a"
)
REVIEW_50_LOCATOR = (
    "//*[@id='tab-pjax-index']/div/div[2]/div[6]/table/tbody/tr[3]/td[2]/a"
)
FALLBACK_CONTAINER_SERVICE_PRICES = (
    "body > div.page.page--blue > main"  # широкий контейнер на .pro
)
CITY_NAME_AND_STAR_LOCATOR = '//*[@id="tab-pjax-index"]/div/div[2]/div[6]/table/tbody/tr[1]/td[2]/a'

FLAG_ON_TABLE_FOR_DELETE = "#yii-debug-toolbar > div.yii-debug-toolbarbar > div.yii-debug-toolbarblock.yii-debug-toolbar__title > a > img"
TG_LOCATOR = "body > div.page.page--blue > i"
TG_BODY_ADD = "body > div.page.page--blue > section.js-block.thpro-tg-infoblock"
WE_USE_COOKIES = '#cookie-agreement'
POLL_OVERLAY_SELECTORS = [
    # точечно под ваш HTML
    ".lsfw-popup-wrap",
    ".lsfw-popup",
    ".pp-user-poll",
    ".lsfw-popup__grey",
    ".lsfw-popup__btn-cross",  # иногда только крестик сверху
    # более общие случаи
    "[class*='popup-wrap']",
    "[class*='popup']",
    "[class*='modal']",
    "[class*='overlay']",
    "[class*='backdrop']",
    "[aria-modal='true']",
    "[role='dialog']",
    "#container > div.good-offer-wrap > section",
    "body > div.fixed-info-icons.no-select-text",
    "#pp-trip-poll-open",
    "#appThChumodan > section",
    '//*[@id="appThChumodan"]/section',
    TG_BODY_ADD,
    TG_LOCATOR,
    FLAG_ON_TABLE_FOR_DELETE,
    WE_USE_COOKIES
]
