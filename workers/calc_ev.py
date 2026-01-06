import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.ev import american_to_prob, vig_stripped_prob, ev
from services.db import supabase

# Example: compute EV for last 100 odds pairs
def calc_sample_ev():
    rows = supabase.table("odds_snapshots").select("*").limit(100).execute().data
    for r in rows:
        price = r["price"]
        if price is None:
            continue
        prob = american_to_prob(price)
        expected_value = ev(prob, price)
        print(f"{r['market_label']} ({price}): EV={expected_value:.3f}")


if __name__ == "__main__":
    calc_sample_ev()

