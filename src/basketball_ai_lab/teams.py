"""Identidades oficiales conocidas de las 30 franquicias NBA.

Los identificadores ESPN se recuperan del proveedor; jamás se inventa un escudo.
Las abreviaturas se usan para cruzar calendarios/cuotas conservadoramente.
"""
import re
import unicodedata

NBA_TEAMS = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

ALIASES = {
    "BRK": "BKN", "BK": "BKN", "GS": "GSW", "GSW": "GSW",
    "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA",
    "WSH": "WAS", "PHO": "PHX", "PHX": "PHX",
    "L.A. CLIPPERS": "LAC", "LOS ANGELES CLIPPERS": "LAC",
    "LOS ANGELES LAKERS": "LAL", "LA LAKERS": "LAL", "LA CLIPPERS": "LAC",
}

def clean(value):
    text=unicodedata.normalize("NFKD", str(value or ""))
    text="".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()

_LOOKUP = {}
for abbr, name in NBA_TEAMS.items():
    _LOOKUP[clean(abbr)] = abbr
    _LOOKUP[clean(name)] = abbr
for alias, abbr in ALIASES.items():
    _LOOKUP[clean(alias)] = abbr

def canonical(name):
    """Return one unique NBA code; never guess from partial names."""
    return _LOOKUP.get(clean(name))
