def american_to_prob(odds: int) -> float:
    if odds < 0:
        return (-odds) / ((-odds) + 100)
    return 100 / (odds + 100)


def vig_stripped_prob(over_prob: float, under_prob: float):
    total = over_prob + under_prob
    if total == 0:
        return over_prob, under_prob
    return over_prob / total, under_prob / total


def ev(true_prob: float, american_odds: int) -> float:
    if american_odds > 0:
        payout = american_odds / 100
    else:
        payout = 100 / (-american_odds)
    return (true_prob * payout) - (1 - true_prob)

