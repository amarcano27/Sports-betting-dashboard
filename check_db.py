import sys; sys.path.insert(0,'.')
from services.db import supabase
from collections import Counter
games = supabase.table('games').select('sport,away_team,home_team').order('sport').execute().data
counts = Counter(g['sport'] for g in games)
print('Games in DB:', dict(counts))
mlb = [g for g in games if g['sport']=='MLB']
for g in mlb:
    print(f"  MLB: {g['away_team']} @ {g['home_team']}")
for g in [g for g in games if g['sport']=='NHL']:
    print(f"  NHL: {g['away_team']} @ {g['home_team']}")
for g in [g for g in games if g['sport']=='NBA']:
    print(f"  NBA: {g['away_team']} @ {g['home_team']}")
odds = supabase.table('odds_snapshots').select('id').limit(9999).execute().data
print(f"Total odds rows: {len(odds)}")
