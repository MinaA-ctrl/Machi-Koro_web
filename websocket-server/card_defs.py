CARD_DEFS = {
    # ── Blue (Primary) — activate on anyone's turn ─────────────────────────────
    'wheat_field':       {'id': 'wheat_field',       'name': 'Wheat Field',       'dice': [1],        'type': 'Blue Primary',    'cost': 1,  'symbol': 'wheat',   'effect': 'Get 1 coin from the bank.'},
    'ranch':             {'id': 'ranch',              'name': 'Ranch',             'dice': [2],        'type': 'Blue Primary',    'cost': 1,  'symbol': 'cow',     'effect': 'Get 1 coin from the bank.'},
    'forest':            {'id': 'forest',             'name': 'Forest',            'dice': [5],        'type': 'Blue Primary',    'cost': 3,  'symbol': 'gear',    'effect': 'Get 1 coin from the bank.'},
    'mine':              {'id': 'mine',               'name': 'Mine',              'dice': [9],        'type': 'Blue Primary',    'cost': 6,  'symbol': 'gear',    'effect': 'Get 5 coins from the bank.'},
    'apple_orchard':     {'id': 'apple_orchard',      'name': 'Apple Orchard',     'dice': [10],       'type': 'Blue Primary',    'cost': 3,  'symbol': 'wheat',   'effect': 'Get 3 coins from the bank.'},
    'flower_garden':     {'id': 'flower_garden',      'name': 'Flower Garden',     'dice': [4],        'type': 'Blue Primary',    'cost': 2,  'symbol': 'wheat',   'effect': 'Get 1 coin from the bank.'},
    'mackerel_boat':     {'id': 'mackerel_boat',      'name': 'Mackerel Boat',     'dice': [8],        'type': 'Blue Primary',    'cost': 3,  'symbol': 'fish',    'effect': 'If you have Harbor, get 3 coins from the bank.', 'requires_landmark': 'harbor'},
    'tuna_boat':         {'id': 'tuna_boat',          'name': 'Tuna Boat',         'dice': [12,13,14], 'type': 'Blue Primary',    'cost': 5,  'symbol': 'fish',    'effect': 'If you have Harbor, roll both dice and get that many coins.', 'requires_landmark': 'harbor'},

    # ── Green (Secondary) — activate on your turn only ─────────────────────────
    'bakery':            {'id': 'bakery',             'name': 'Bakery',            'dice': [2,3],      'type': 'Green Secondary', 'cost': 1,  'symbol': 'bread',   'effect': 'Get 1 coin from the bank.'},
    'convenience_store': {'id': 'convenience_store',  'name': 'Convenience Store', 'dice': [4],        'type': 'Green Secondary', 'cost': 2,  'symbol': 'bread',   'effect': 'Get 3 coins from the bank.'},
    'cheese_factory':    {'id': 'cheese_factory',     'name': 'Cheese Factory',    'dice': [7],        'type': 'Green Secondary', 'cost': 5,  'symbol': 'factory', 'effect': 'Get 3 coins per Ranch you own.'},
    'furniture_factory': {'id': 'furniture_factory',  'name': 'Furniture Factory', 'dice': [8],        'type': 'Green Secondary', 'cost': 3,  'symbol': 'factory', 'effect': 'Get 3 coins per Forest or Mine you own.'},
    'farmers_market':    {'id': 'farmers_market',     'name': 'Farmers Market',    'dice': [11,12],    'type': 'Green Secondary', 'cost': 2,  'symbol': 'fruit',   'effect': 'Get 2 coins per wheat-symbol card you own.'},
    'flower_shop':       {'id': 'flower_shop',        'name': 'Flower Shop',       'dice': [6],        'type': 'Green Secondary', 'cost': 1,  'symbol': 'bread',   'effect': 'Get 1 coin per Flower Garden you own.'},
    'food_warehouse':    {'id': 'food_warehouse',     'name': 'Food Warehouse',    'dice': [12,13],    'type': 'Green Secondary', 'cost': 2,  'symbol': 'factory', 'effect': 'If you have Harbor, get 2 coins per cup-symbol card you own.', 'requires_landmark': 'harbor'},

    # ── Red (Restaurant) — activate on opponent's turn ─────────────────────────
    'cafe':              {'id': 'cafe',               'name': 'Café',              'dice': [3],        'type': 'Red Restaurant',  'cost': 2,  'symbol': 'cup',     'effect': 'Take 1 coin from the active player.'},
    'family_restaurant': {'id': 'family_restaurant',  'name': 'Family Restaurant', 'dice': [9,10],     'type': 'Red Restaurant',  'cost': 3,  'symbol': 'cup',     'effect': 'Take 2 coins from the active player.'},
    'sushi_bar':         {'id': 'sushi_bar',          'name': 'Sushi Bar',         'dice': [1],        'type': 'Red Restaurant',  'cost': 2,  'symbol': 'cup',     'effect': 'If you have Harbor, take 3 coins from the active player.', 'requires_landmark': 'harbor'},
    'hamburger_stand':   {'id': 'hamburger_stand',    'name': 'Hamburger Stand',   'dice': [8],        'type': 'Red Restaurant',  'cost': 1,  'symbol': 'cup',     'effect': 'Take 1 coin from the active player.'},
    'pizza_joint':       {'id': 'pizza_joint',        'name': 'Pizza Joint',       'dice': [7],        'type': 'Red Restaurant',  'cost': 1,  'symbol': 'cup',     'effect': 'Take 1 coin from the active player.'},

    # ── Purple (Major) — activate on your turn, max 1 per player ───────────────
    'stadium':           {'id': 'stadium',            'name': 'Stadium',           'dice': [6],        'type': 'Purple Major',    'cost': 6,  'symbol': 'tower',   'effect': 'Take 2 coins from each opponent.', 'max_per_player': 1},
    'tv_station':        {'id': 'tv_station',         'name': 'TV Station',        'dice': [6],        'type': 'Purple Major',    'cost': 7,  'symbol': 'tower',   'effect': 'Take 5 coins from any one opponent.', 'max_per_player': 1},
    'business_center':   {'id': 'business_center',    'name': 'Business Center',   'dice': [6],        'type': 'Purple Major',    'cost': 8,  'symbol': 'tower',   'effect': 'Trade one non-Major establishment with an opponent.', 'max_per_player': 1},
    'publisher':         {'id': 'publisher',          'name': 'Publisher',         'dice': [7],        'type': 'Purple Major',    'cost': 5,  'symbol': 'tower',   'effect': 'Take 1 coin per cup/bread symbol card from each opponent.', 'max_per_player': 1},
    'tax_office':        {'id': 'tax_office',         'name': 'Tax Office',        'dice': [8,9],      'type': 'Purple Major',    'cost': 4,  'symbol': 'tower',   'effect': 'Take half coins (rounded down) from each opponent with 10+ coins.', 'max_per_player': 1},
}

LANDMARK_DEFS = [
    {'id': 'city_hall',      'name': 'City Hall',      'cost': 0,  'pre_built': True,  'effect': 'After income, if you have 0 coins, get 1 coin from the bank.'},
    {'id': 'harbor',         'name': 'Harbor',         'cost': 2,  'pre_built': False, 'effect': 'When you roll 10+, you may add 2 to the total.'},
    {'id': 'train_station',  'name': 'Train Station',  'cost': 4,  'pre_built': False, 'effect': 'You may choose to roll 1 or 2 dice each turn.'},
    {'id': 'shopping_mall',  'name': 'Shopping Mall',  'cost': 10, 'pre_built': False, 'effect': 'Your cup and bread establishments earn +1 coin each.'},
    {'id': 'amusement_park', 'name': 'Amusement Park', 'cost': 16, 'pre_built': False, 'effect': 'If you roll doubles, take another turn.'},
    {'id': 'radio_tower',    'name': 'Radio Tower',    'cost': 22, 'pre_built': False, 'effect': 'Once per turn, you may reroll the dice.'},
    {'id': 'airport',        'name': 'Airport',        'cost': 30, 'pre_built': False, 'effect': 'If you do not build, get 10 coins.'},
]

WHEAT_SYMBOL_CARDS = {'wheat_field', 'apple_orchard', 'flower_garden'}  # ranch is cow symbol, not wheat
CUP_SYMBOL_CARDS   = {'cafe', 'sushi_bar', 'hamburger_stand', 'pizza_joint', 'family_restaurant'}
BREAD_SYMBOL_CARDS = {'bakery', 'convenience_store', 'flower_shop'}
GEAR_SYMBOL_CARDS  = {'forest', 'mine'}
