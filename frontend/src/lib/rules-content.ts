/**
 * Player-facing rules, grounded in the engine (machi_koro_engine/card_defs.py +
 * game_config.py). Four rule sets: the Basic game, the Harbour expansion, the
 * Millionaire's Row (Sharp) add-on, and the 10-card Variable-Supply market mode.
 * Localized EN/RU; the Rules page picks the set for the active locale.
 */
export interface RuleBlock {
  heading: string
  points: string[]
}
export interface RuleSet {
  id: 'basic' | 'harbour' | 'sharp' | 'variable'
  title: string
  blurb: string
  blocks: RuleBlock[]
}

const EN: RuleSet[] = [
  {
    id: 'basic',
    title: 'Basic Game',
    blurb: 'The core city-building dice game — finish building your city first to win.',
    blocks: [
      {
        heading: 'Goal',
        points: [
          'Be the first player to build all four of your Landmarks: Train Station, Shopping Mall, Amusement Park and Radio Tower.',
        ],
      },
      {
        heading: 'Setup',
        points: [
          'Each player starts with one Wheat Field, one Bakery and 3 coins.',
          'The market in the middle holds the establishments anyone may buy.',
        ],
      },
      {
        heading: 'Your turn — 3 steps',
        points: [
          '1. Roll the dice — roll one die (you may roll two once your Train Station is built).',
          '2. Earn income — every establishment whose number matches the roll pays out, following the colour order below.',
          '3. Build — buy one establishment from the market, build one Landmark, or pass. You do only one of these each turn.',
        ],
      },
      {
        heading: 'Card colours (when they pay)',
        points: [
          '🔵 Blue – Primary industry: pays you from the bank on ANY player’s turn.',
          '🟢 Green – Secondary industry: pays you from the bank, but only on YOUR turn.',
          '🔴 Red – Restaurants: take coins from the player who rolled, on OTHER players’ turns.',
          '🟣 Purple – Major establishments: trigger only on YOUR turn and hit your opponents. You may own only one of each.',
        ],
      },
      {
        heading: 'Resolving a roll',
        points: [
          'If one number triggers several colours, pay them in order: Red restaurants first, then Blue & Green, then Purple.',
          'If the active player can’t pay a restaurant in full, they pay everything they have — no one goes into debt.',
        ],
      },
      {
        heading: 'Your Landmarks (the powers you unlock)',
        points: [
          '🚉 Train Station (4) – you may roll one or two dice each turn.',
          '🏬 Shopping Mall (10) – your 🍞 bread and ☕ cup establishments each earn +1 coin.',
          '🎡 Amusement Park (16) – roll doubles and you take another turn.',
          '📻 Radio Tower (22) – once per turn you may reroll your dice.',
        ],
      },
    ],
  },
  {
    id: 'harbour',
    title: 'Harbour',
    blurb: 'The Base game plus the Harbor expansion: sea-side cards, higher dice totals and extra Landmarks.',
    blocks: [
      {
        heading: 'What’s different',
        points: [
          'You build more Landmarks to win. City Hall starts already built; you must construct the Harbor, Train Station, Shopping Mall, Amusement Park, Radio Tower and the Airport.',
          'New establishments can activate on totals of 10 or more, so big two-dice rolls finally matter.',
        ],
      },
      {
        heading: 'New Landmarks',
        points: [
          '🏛️ City Hall (already built) – after collecting income, if you have 0 coins, take 1 from the bank.',
          '⚓ Harbor (2) – when you roll a total of 10 or more, you may add 2 to it.',
          '✈️ Airport (30) – if you build nothing on your turn, take 10 coins instead.',
        ],
      },
      {
        heading: 'New establishments',
        points: [
          '🐟 Mackerel Boat (8) – needs the Harbor; earns 3 coins from the bank.',
          '🐟 Tuna Boat (12–14) – needs the Harbor; roll both dice and earn that many coins (everyone with a Tuna Boat shares the same roll).',
          '🍣 Sushi Bar (1) – needs the Harbor; take 3 coins from the active player.',
          '🏭 Food Warehouse (12–13) – needs the Harbor; earn 2 coins per ☕ cup card you own.',
        ],
      },
    ],
  },
  {
    id: 'sharp',
    title: 'Millionaire’s Row',
    blurb: 'An add-on you can layer onto Basic or Harbour. It adds aggressive, interactive cards that shake up the leader.',
    blocks: [
      {
        heading: 'How it works',
        points: [
          'Millionaire’s Row mixes its cards into the supply. Several are interactive — when they trigger, the game asks you to make a choice.',
          'A card “closed for renovation” stays inactive until its owner next rolls that number.',
        ],
      },
      {
        heading: 'New Major (purple) establishments',
        points: [
          '🏟️ Stadium (6) – take 2 coins from every opponent.',
          '📺 TV Station (6) – take 5 coins from one opponent of your choice.',
          '🏢 Business Center (6) – swap one of your non-Major establishments for one of an opponent’s.',
          '📰 Publisher (7) – take 1 coin per 🍞/☕ card from each opponent.',
          '🏦 Tax Office (8–9) – from each opponent holding 10+ coins, take half (rounded down).',
          '🚀 Tech Startup (10) – on your turn you may invest 1 coin onto it; when it triggers, each opponent pays you the full invested amount.',
          '🌳 Park (11–13) – pool every player’s coins and split them back equally (the active player keeps any remainder).',
          '🧹 Cleaning Company (8) – close every copy of one establishment type across all players, and collect 1 coin per copy closed.',
        ],
      },
      {
        heading: 'New Blue / Green / Red cards',
        points: [
          '🌽 Corn Field (3–4, blue) – if you have 1 or fewer Landmarks, get 1 coin.',
          '🏪 General Store (2, green) – on your turn, if you have 1 or fewer Landmarks, get 2 coins.',
          '🍷 Winery (9, green) – earn 6 coins per Vineyard you own, then it closes for renovation.',
          '💵 Loan Office (5–6, green) – take 5 coins when you build it; pay 2 each time it activates.',
          '🚚 Moving Company (9–10, green) – give one non-Major establishment to another player, then get 4 coins.',
          '💣 Demolition Company (4, green) – demolish one of your built Landmarks (never City Hall) and get 8 coins.',
          '🍴 French Restaurant (5, red) – if the active player has 2+ Landmarks, take 5 coins from them.',
          '🥢 Private Club (12–14, red) – if the active player has 3+ Landmarks, take ALL their coins.',
        ],
      },
    ],
  },
  {
    id: 'variable',
    title: '10-Card Market',
    blurb: 'A tidier way to lay out the market — it turns on automatically with Millionaire’s Row.',
    blocks: [
      {
        heading: 'How it works',
        points: [
          'Instead of every card type being on the table, only 10 different establishment types are face-up at any time.',
          'When a stack sells out, the empty slot is immediately refilled with the next type drawn from a shuffled deck — so the market keeps changing.',
          'Each stack shows how many copies are left (e.g. ×3).',
        ],
      },
      {
        heading: 'Why use it',
        points: [
          'It keeps the table compact and adds tension: the card you want can sell out, and a brand-new type can appear at any moment.',
          'It’s on by default when Millionaire’s Row is active; you can toggle it on or off when creating a table.',
        ],
      },
    ],
  },
]

const RU: RuleSet[] = [
  {
    id: 'basic',
    title: 'Базовая игра',
    blurb: 'Основная игра про строительство города — постройте свой город первым, чтобы победить.',
    blocks: [
      {
        heading: 'Цель',
        points: [
          'Первым постройте все четыре свои достопримечательности: Вокзал, Торговый центр, Парк аттракционов и Радиовышку.',
        ],
      },
      {
        heading: 'Подготовка',
        points: [
          'Каждый игрок начинает с одного Пшеничного поля, одной Пекарни и 3 монет.',
          'В центре — рынок с заведениями, которые может купить любой игрок.',
        ],
      },
      {
        heading: 'Ваш ход — 3 шага',
        points: [
          '1. Бросок — бросьте один кубик (можно два, как только построен Вокзал).',
          '2. Доход — каждое заведение, чей номер совпал с броском, приносит монеты в порядке цветов (ниже).',
          '3. Строительство — купите одно заведение с рынка, постройте одну достопримечательность или пропустите. За ход — только одно из этого.',
        ],
      },
      {
        heading: 'Цвета карт (когда платят)',
        points: [
          '🔵 Синие — первичная индустрия: платят вам из банка в ход ЛЮБОГО игрока.',
          '🟢 Зелёные — вторичная индустрия: платят вам из банка, но только в ВАШ ход.',
          '🔴 Красные — рестораны: забирают монеты у того, кто бросил кубик, в ходы ДРУГИХ игроков.',
          '🟣 Фиолетовые — крупные предприятия: срабатывают только в ВАШ ход и бьют по соперникам. Каждого — не больше одного.',
        ],
      },
      {
        heading: 'Порядок выплат',
        points: [
          'Если один номер запускает несколько цветов, платите по порядку: сначала красные рестораны, затем синие и зелёные, затем фиолетовые.',
          'Если активный игрок не может полностью заплатить ресторану, он отдаёт всё, что есть — в долг никто не уходит.',
        ],
      },
      {
        heading: 'Ваши достопримечательности (открывают способности)',
        points: [
          '🚉 Вокзал (4) — можно бросать один или два кубика за ход.',
          '🏬 Торговый центр (10) — ваши заведения с 🍞 и ☕ приносят +1 монету каждое.',
          '🎡 Парк аттракционов (16) — выпал дубль — берёте ещё один ход.',
          '📻 Радиовышка (22) — раз за ход можно перебросить кубики.',
        ],
      },
    ],
  },
  {
    id: 'harbour',
    title: 'Гавань',
    blurb: 'Базовая игра плюс дополнение «Гавань»: морские карты, большие суммы на кубиках и новые достопримечательности.',
    blocks: [
      {
        heading: 'Что меняется',
        points: [
          'Для победы нужно построить больше достопримечательностей. Ратуша уже построена; нужно возвести Гавань, Вокзал, Торговый центр, Парк аттракционов, Радиовышку и Аэропорт.',
          'Новые заведения срабатывают на суммах 10 и больше — крупные броски двумя кубиками наконец-то важны.',
        ],
      },
      {
        heading: 'Новые достопримечательности',
        points: [
          '🏛️ Ратуша (уже построена) — после дохода, если у вас 0 монет, возьмите 1 из банка.',
          '⚓ Гавань (2) — при сумме 10 и больше можно добавить к ней 2.',
          '✈️ Аэропорт (30) — если в свой ход вы ничего не строите, возьмите 10 монет.',
        ],
      },
      {
        heading: 'Новые заведения',
        points: [
          '🐟 Лодка для макрели (8) — нужна Гавань; приносит 3 монеты из банка.',
          '🐟 Лодка для тунца (12–14) — нужна Гавань; бросьте оба кубика и получите столько монет (все владельцы получают один и тот же бросок).',
          '🍣 Суши-бар (1) — нужна Гавань; заберите 3 монеты у активного игрока.',
          '🏭 Продовольственный склад (12–13) — нужна Гавань; 2 монеты за каждую вашу карту с ☕.',
        ],
      },
    ],
  },
  {
    id: 'sharp',
    title: 'Улица миллионеров',
    blurb: 'Дополнение поверх Базовой игры или Гавани. Добавляет агрессивные интерактивные карты, бьющие по лидеру.',
    blocks: [
      {
        heading: 'Как это работает',
        points: [
          '«Улица миллионеров» подмешивает свои карты в рынок. Некоторые интерактивны — при срабатывании игра просит вас сделать выбор.',
          'Карта «закрыта на ремонт» не работает, пока её владелец снова не выбросит её номер.',
        ],
      },
      {
        heading: 'Новые крупные (фиолетовые) предприятия',
        points: [
          '🏟️ Стадион (6) — заберите 2 монеты у каждого соперника.',
          '📺 Телестудия (6) — заберите 5 монет у одного соперника на выбор.',
          '🏢 Бизнес-центр (6) — обменяйте одно своё не-крупное заведение на заведение соперника.',
          '📰 Издательство (7) — 1 монета за каждую карту 🍞/☕ у каждого соперника.',
          '🏦 Налоговая (8–9) — у каждого соперника с 10+ монетами заберите половину (с округлением вниз).',
          '🚀 Технологический стартап (10) — в свой ход можно вложить 1 монету; при срабатывании каждый соперник платит вам всю вложенную сумму.',
          '🌳 Парк (11–13) — соберите монеты всех игроков и разделите поровну (остаток — активному игроку).',
          '🧹 Клининговая компания (8) — закройте все копии одного типа заведения у всех игроков и получите 1 монету за каждую закрытую копию.',
        ],
      },
      {
        heading: 'Новые синие / зелёные / красные карты',
        points: [
          '🌽 Кукурузное поле (3–4, синяя) — если у вас не больше 1 достопримечательности, получите 1 монету.',
          '🏪 Универмаг (2, зелёная) — в свой ход, если у вас не больше 1 достопримечательности, получите 2 монеты.',
          '🍷 Винодельня (9, зелёная) — 6 монет за каждый ваш Виноградник, затем закрывается на ремонт.',
          '💵 Кредитная контора (5–6, зелёная) — 5 монет при постройке; платите 2 каждый раз при срабатывании.',
          '🚚 Транспортная компания (9–10, зелёная) — отдайте одно не-крупное заведение другому игроку и получите 4 монеты.',
          '💣 Снос (4, зелёная) — снесите одну свою построенную достопримечательность (кроме Ратуши) и получите 8 монет.',
          '🍴 Французский ресторан (5, красная) — если у активного игрока 2+ достопримечательности, заберите у него 5 монет.',
          '🥢 Закрытый клуб (12–14, красная) — если у активного игрока 3+ достопримечательности, заберите ВСЕ его монеты.',
        ],
      },
    ],
  },
  {
    id: 'variable',
    title: 'Рынок из 10 карт',
    blurb: 'Более компактная раскладка рынка — включается автоматически вместе с «Улицей миллионеров».',
    blocks: [
      {
        heading: 'Как это работает',
        points: [
          'Вместо всех типов карт на столе одновременно лежат только 10 разных типов заведений.',
          'Когда стопка распродана, пустой слот сразу заполняется следующим типом из перемешанной колоды — рынок постоянно меняется.',
          'На каждой стопке показано, сколько копий осталось (например, ×3).',
        ],
      },
      {
        heading: 'Зачем это нужно',
        points: [
          'Стол остаётся компактным и появляется напряжение: нужная карта может закончиться, а новый тип — появиться в любой момент.',
          'По умолчанию включён вместе с «Улицей миллионеров»; при создании стола его можно включить или выключить.',
        ],
      },
    ],
  },
]

// `en` is required (the guaranteed fallback); other locales are optional.
export const RULES: Record<string, RuleSet[]> & { en: RuleSet[] } = { en: EN, ru: RU }
