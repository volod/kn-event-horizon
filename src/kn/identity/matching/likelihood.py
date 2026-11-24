"""Numerically stable Fellegi-Sunter likelihood and posterior."""

import math


def weight(m: float, u: float) -> float:
    return math.log(m) - math.log(u)


def posterior(prior: float, score: float) -> float:
    log_odds = math.log(prior) - math.log1p(-prior) + score
    if log_odds >= 0:
        return 1 / (1 + math.exp(-log_odds))
    odds = math.exp(log_odds)
    return odds / (1 + odds)
