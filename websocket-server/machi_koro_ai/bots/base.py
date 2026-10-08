"""The one question every bot answers."""


class Bot:
    name = "Bot"

    def choose(self, state, seat, legal_moves):
        """Return one move from `legal_moves` (never empty) for `seat` in `state`.

        `state` must be treated as read-only. Returning a move that isn't in
        `legal_moves` is a bug — the game will raise IllegalMove."""
        raise NotImplementedError
