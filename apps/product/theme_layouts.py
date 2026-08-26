PRODUCT_THEME_SLOT_COUNTS = {
    0: 3,
    1: 3,
    2: 3,
    3: 3,
    4: 3,
    5: 3,
    6: 2,
    7: 2,
    8: 2,
    9: 1,
    10: 1,
    11: 1,
    12: 3,
    13: 3,
    14: 3,
    15: 2,
    16: 2,
    17: 2,
}


def product_theme_slot_count(order):
    return PRODUCT_THEME_SLOT_COUNTS.get(order, 0)
