TOP_ELEMENT_LOCATOR = '#container > div.topline'
POPULARS_LOCATOR = '#container > div.js-start-fixed-btn.grid > article > div.card-hotel-wrap > section.stata-bubble.stata-bubble--fz13-laptop.no-scrollbar'
REVIEW_LOCATOR = '#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section'
ATTENDANCE_LOCATOR = '#pg-container-stat > div:nth-child(1)'
ACTIVITY_LOCATOR = '#tab-pjax-index > div.js-bth__tbl.js-act-long-view'
RATING_HOTEL_IN_HURGHADA_LOCATOR = '.bth__scrolable-tbl .bth__table--bordering'
SERVICES_AND_PRICES_LOCATOR = '#hotelProfileApp > table:nth-child(5)'
TG_HIDE_LOCATOR = "section.js-block.thpro-tg-infoblock > i"
ALL_TABLE_RATING_OVEREVIEW_LOCATOR = '#tab-pjax-index > div > div.js-act-long-view'
FLAG_LOCATOR = 'body > div.page > header > section > div.header__r-col.header__r-col--abs-right > div > div > button > i'
COUNT_REVIEW_LOCATOR = '#container > div.card-hotel-wrap.mt30 > section:nth-child(3) > div > section > ' \
                       'div.card-hotel-rating-list > ul:nth-child(4) > li:nth-child(1) > b'
INCORRECT_DATA_SELECTOR = '#cstm-filter-frm > article > div.js-filter-info.filter-new__info-wrap'
ACTIVATION_REQUIRES_SELECTOR = '#pg-container-stat > div > table'
REVIEW_10_LOCATOR = '#tab-pjax-index > div > div.js-act-long-view > div:nth-child(5) > table > tbody > ' \
                    'tr:nth-child(2) > td:nth-child(2) > a'
REVIEW_50_LOCATOR = '#tab-pjax-index > div > div.js-act-long-view > div:nth-child(5) > table > tbody > ' \
                    'tr:nth-child(3) > td:nth-child(2) > a'
FLAG_ON_TABLE_FOR_DELETE = '#yii-debug-toolbar > div.yii-debug-toolbarbar > div.yii-debug-toolbarblock.yii-debug-toolbar__title > a > img'
TG_LOCATOR = 'body > div.page.page--blue > i'
TG_BODY_ADD = 'body > div.page.page--blue > section.js-block.thpro-tg-infoblock'
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
    '#pp-trip-poll-open',
    "#appThChumodan > section",
    TG_BODY_ADD,
    TG_LOCATOR,
    FLAG_ON_TABLE_FOR_DELETE
]
