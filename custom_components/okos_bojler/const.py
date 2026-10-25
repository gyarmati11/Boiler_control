"""Okos Bojler – konstansok."""
from __future__ import annotations

DOMAIN = "okos_bojler"
VERSION = "1.1.0"

CONF_NAME = "name"
CONF_SWITCH = "switch_entity"
CONF_BATTERY = "battery_entity"
CONF_EV = "ev_entity"

PLATFORMS = ["sensor", "number", "select", "switch", "button", "time"]

STORAGE_VERSION = 1

# Üzemmódok
MODE_AUTO = "Automatikus"
MODE_OFF = "Mindig ki"
MODE_ON = "Mindig be"
MODES = [MODE_AUTO, MODE_OFF, MODE_ON]

DEFAULT_SETTINGS: dict = {
    "mode": MODE_AUTO,
    "on_threshold": 90.0,      # % – e fölött napelemes fűtés indul
    "off_threshold": 85.0,     # % – ez alatt napelemes fűtés leáll (hiszterézis)
    "min_minutes": 120.0,      # perc – napi minimum fűtés
    "turbo_hours": 3.0,        # óra – turbó időtartam
    "power_kw": 2.0,           # kW – bojler teljesítménye (energia becsléshez)
    "backup_start": "15:00",   # tartalék fűtés ablak kezdete
    "backup_end": "21:00",     # tartalék fűtés ablak vége
    "solar_enabled": True,     # napelemes (akkus) fűtés engedélyezve
    "backup_enabled": True,    # tartalék minimum fűtés engedélyezve
    "count_solar": True,       # napközbeni fűtés beleszámít a minimumba
    "night_block": True,       # éjszakai tiltás
    "night_start": "22:00",    # éjszakai tiltás kezdete
    "night_end": "06:00",      # éjszakai tiltás vége
    "ev_block": True,          # autótöltés alatt tiltás
    "ev_threshold_w": 500.0,   # W – e felett számít töltésnek (teljesítmény szenzornál)
}

# Állapot okok (kulcs -> magyar felirat)
REASONS = {
    "napelem": "Napelemes fűtés",
    "tartalek": "Tartalék fűtés",
    "turbo": "Turbó fűtés",
    "kezi": "Kézi bekapcsolás",
    "kikapcsolva": "Kikapcsolva",
    "ejszaka": "Éjszakai tiltás",
    "autotoltes": "Autótöltés – szünetel",
    "teljesitve": "Napi minimum teljesítve",
    "var": "Várakozás",
}

# Fűtési idő elszámolás kategóriái
HEAT_KEYS = ["napelem", "tartalek", "turbo", "kezi", "egyeb"]
