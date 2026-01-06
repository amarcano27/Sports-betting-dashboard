"""
Team name mapping between different formats
"""
TEAM_MAPPING = {
    # Full name to abbreviation
    "Los Angeles Clippers": "LAC",
    "Phoenix Suns": "PHX",
    "New York Knicks": "NYK",
    "Los Angeles Lakers": "LAL",
    "Boston Celtics": "BOS",
    "Golden State Warriors": "GSW",
    "Miami Heat": "MIA",
    "Denver Nuggets": "DEN",
    "Milwaukee Bucks": "MIL",
    "Philadelphia 76ers": "PHI",
    "Brooklyn Nets": "BKN",
    "Atlanta Hawks": "ATL",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Detroit Pistons": "DET",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Memphis Grizzlies": "MEM",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
    "Charlotte Hornets": "CHA",
}

def get_team_abbrev(full_name):
    """Convert full team name to abbreviation"""
    return TEAM_MAPPING.get(full_name, full_name)

def normalize_team_name(team_name):
    """Normalize team name for matching"""
    if not team_name:
        return ""
    
    # Try direct mapping
    abbrev = get_team_abbrev(team_name)
    if abbrev != team_name:
        return abbrev
    
    # Try to extract abbreviation from full name
    words = team_name.split()
    if len(words) >= 2:
        # Try last word or common patterns
        last_word = words[-1]
        if last_word in ["Clippers", "Suns", "Knicks", "Lakers", "Celtics", "Warriors"]:
            # Extract city + last word
            city = words[0] if len(words) > 1 else ""
            if city == "Los" and "Angeles" in team_name:
                city = "LAL" if "Lakers" in team_name else "LAC"
            elif city == "Golden" and "State" in team_name:
                city = "GSW"
            elif city == "New" and "York" in team_name:
                city = "NYK"
            elif city == "New" and "Orleans" in team_name:
                city = "NOP"
            elif city == "Oklahoma" and "City" in team_name:
                city = "OKC"
            elif city == "Portland" in team_name:
                city = "POR"
            elif city == "San" and "Antonio" in team_name:
                city = "SAS"
            else:
                city = words[0][:3].upper()
            return city
    
    return team_name

