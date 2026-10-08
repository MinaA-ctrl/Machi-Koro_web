"""How the AI sees the game (numbers) and how it acts (a fixed numbered menu).

    enc = Encoding(make_config("basic"), n_players=2)
    obs  = enc.observe(state, seat)          # the board as numbers, from `seat`'s view
    mask = enc.mask(state, seat)             # which menu items are allowed right now
    move = enc.action_to_move(i, state, seat)   # menu number → engine move
    i    = enc.move_to_action(move, state, seat) # engine move → menu number

Everything is from the deciding player's point of view: "me" first, then the
other players in turn order. That way one brain can play from any seat.

Only public information goes in: coins, cards, landmarks, supply, phase, dice.
The hidden Variable Supply deck order is never read (plan S2).

Supported: Basic and Harbour, any player count. Sharp's extra decisions
(Cleaning/Demolition/Moving Company, Tech Startup) aren't in the menu yet.
"""
import numpy as np

from machi_koro_engine import CARD_DEFS, legal_actions

# Phases in which the AI makes a decision (Sharp-only phases not supported yet).
PHASES = ("roll", "harbor_prompt", "reroll_prompt", "build",
          "tv_station", "business_center", "tuna_roll")

COIN_SCALE = 20          # coins are divided by this, so typical values are 0–2
COIN_CAP = 100           # …and capped, so a hoard of coins can't blow up the numbers
COUNT_SCALE = 6          # a supply pile holds 6 copies
OBS_HIGH = 10.0          # upper bound for any single number (for the gym space)


class Encoding:
    def __init__(self, config, n_players):
        if config.sharp:
            raise ValueError("Sharp isn't supported by the AI encoding yet")
        self.config = config
        self.n_players = n_players
        self.cards = list(config.establishment_ids)
        self.landmarks = list(config.landmark_ids)
        self.tradeable = [c for c in self.cards if CARD_DEFS[c]["type"] != "Purple Major"]
        opps = range(1, n_players)       # opponents as "1 seat after me", "2 seats after me", …

        # The fixed menu. Each entry is a key; its position is the action number.
        self.actions = (
            [("roll", 1), ("roll", 2), ("answer", True), ("answer", False)]
            + [("buy", c) for c in self.cards]
            + [("landmark", lm) for lm in self.landmarks]
            + [("skip_build",), ("tuna_roll",), ("skip_trade",)]
            + [("tv_station", o) for o in opps]
            + [("trade", mine, o, theirs)
               for o in opps for mine in self.tradeable for theirs in self.tradeable]
        )
        self.index = {key: i for i, key in enumerate(self.actions)}
        self.n_actions = len(self.actions)

        per_player = 1 + len(self.cards) + len(self.landmarks)   # coins, cards, landmarks
        self.obs_size = (n_players * per_player + len(self.cards)   # + supply
                         + len(PHASES) + 13 + 1)                    # + phase, last roll, doubles

    # ── seats ─────────────────────────────────────────────────────────────────

    def _seats_from(self, state, me):
        """Seats in turn order starting with `me`."""
        seats = sorted(p["seat"] for p in state["players"])
        i = seats.index(me)
        return seats[i:] + seats[:i]

    # ── eyes: board → numbers ─────────────────────────────────────────────────

    def observe(self, state, me):
        by_seat = {p["seat"]: p for p in state["players"]}
        x = []
        for seat in self._seats_from(state, me):
            p = by_seat[seat]
            x.append(min(p["coins"], COIN_CAP) / COIN_SCALE)
            x.extend(p["cards"].get(c, 0) / COUNT_SCALE for c in self.cards)
            built = {lm["id"] for lm in p["landmarks"] if lm["built"]}
            x.extend(1.0 if lm in built else 0.0 for lm in self.landmarks)
        x.extend(state["supply"].get(c, 0) / COUNT_SCALE for c in self.cards)
        x.extend(1.0 if state["phase"] == ph else 0.0 for ph in PHASES)
        roll = state.get("last_roll") or 0
        x.extend(1.0 if roll == r else 0.0 for r in range(13))
        x.append(1.0 if state.get("doubles") else 0.0)
        obs = np.asarray(x, dtype=np.float32)
        return np.minimum(obs, OBS_HIGH)

    # ── hands: menu number ↔ engine move ──────────────────────────────────────

    def move_to_action(self, move, state, me):
        e = move["event"]
        if e == "roll":
            key = ("roll", move.get("dice_count", 1))
        elif e == "prompt_response":
            key = ("answer", bool(move["answer"]))
        elif e == "build":
            key = ("buy" if move["type"] == "card" else "landmark", move["id"])
        elif e in ("skip_build", "tuna_roll"):
            key = (e,)
        elif e == "skip_business_center":
            key = ("skip_trade",)
        elif e == "tv_station_pick":
            key = ("tv_station", self._offset(state, me, move["target_seat"]))
        elif e == "business_center":
            key = ("trade", move["my_card"], self._offset(state, me, move["opp_seat"]),
                   move["opp_card"])
        else:
            raise ValueError(f"move not in the AI menu: {move}")
        return self.index[key]

    def action_to_move(self, action, state, me):
        key = self.actions[action]
        kind = key[0]
        if kind == "roll":
            return {"event": "roll", "dice_count": key[1]}
        if kind == "answer":
            return {"event": "prompt_response", "answer": key[1]}
        if kind == "buy":
            return {"event": "build", "type": "card", "id": key[1]}
        if kind == "landmark":
            return {"event": "build", "type": "landmark", "id": key[1]}
        if kind in ("skip_build", "tuna_roll"):
            return {"event": kind}
        if kind == "skip_trade":
            return {"event": "skip_business_center"}
        if kind == "tv_station":
            return {"event": "tv_station_pick", "target_seat": self._seat_at(state, me, key[1])}
        _, mine, offset, theirs = key
        return {"event": "business_center", "my_card": mine,
                "opp_seat": self._seat_at(state, me, offset), "opp_card": theirs}

    def _offset(self, state, me, seat):
        return self._seats_from(state, me).index(seat)

    def _seat_at(self, state, me, offset):
        return self._seats_from(state, me)[offset]

    # ── the mask: which menu items are allowed now ────────────────────────────

    def mask(self, state, me, legal=None):
        legal = legal_actions(state, me) if legal is None else legal
        m = np.zeros(self.n_actions, dtype=bool)
        for move in legal:
            m[self.move_to_action(move, state, me)] = True
        return m

    # ── for people ────────────────────────────────────────────────────────────

    def describe_action(self, action):
        key = self.actions[action]
        name = lambda c: CARD_DEFS[c]["name"] if c in CARD_DEFS else c.replace("_", " ").title()
        kind = key[0]
        if kind == "roll":
            return f"roll {key[1]} {'die' if key[1] == 1 else 'dice'}"
        if kind == "answer":
            return "answer yes" if key[1] else "answer no"
        if kind in ("buy", "landmark"):
            return f"{'buy' if kind == 'buy' else 'build'} {name(key[1])}"
        if kind == "tv_station":
            return f"TV Station: rob the player {key[1]} seat(s) after me"
        if kind == "trade":
            return f"trade my {name(key[1])} for {name(key[3])} of the player {key[2]} seat(s) after me"
        return kind.replace("_", " ")

    def describe_observation(self, obs):
        """Label every number in an observation (for learning / debugging)."""
        labels = []
        for i in range(self.n_players):
            who = "me" if i == 0 else f"opponent {i}"
            labels.append(f"{who}: coins/{COIN_SCALE}")
            labels += [f"{who}: {CARD_DEFS[c]['name']} copies/{COUNT_SCALE}" for c in self.cards]
            labels += [f"{who}: has {lm.replace('_', ' ').title()}" for lm in self.landmarks]
        labels += [f"supply: {CARD_DEFS[c]['name']} left/{COUNT_SCALE}" for c in self.cards]
        labels += [f"phase is {ph}" for ph in PHASES]
        labels += ["no roll yet"] + [f"last roll was {r}" for r in range(1, 13)]
        labels += ["rolled doubles"]
        return list(zip(labels, obs.tolist()))
