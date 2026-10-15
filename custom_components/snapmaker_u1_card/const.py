"""Konstanten."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "snapmaker_u1_card"
VERSION = "1.0.1"

CONF_API_KEY = "api_key"
CONF_FILES_LIMIT = "files_limit"
CONF_POWER_SWITCH = "power_switch"
CONF_POWER_SENSOR = "power_sensor"
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_ENERGY_PRICE = "energy_price"  # Preis-Entitaet (sensor/input_number)
CONF_AUTO_ON = "auto_on"
CONF_NOTIFY = "notify_targets"
CONF_NOTIFY_EVENTS = "notify_events"
CONF_CAMERA = "camera"
CONF_SPOOLMAN_URL = "spoolman_url"
CONF_SPOOLMAN_DEDUCT = "spoolman_deduct"
CONF_SPOOLMAN_LOW = "spoolman_low"
CONF_FILAMENT_PRICES = "filament_prices"  # {"PLA": 20.0, ...} je kg
CONF_SHUTDOWN_HOST = "shutdown_host"
CONF_AUTO_OFF = "auto_off"
CONF_AUTO_OFF_TEMP = "auto_off_temp"
CONF_AUTO_OFF_DELAY = "auto_off_delay"
CONF_ARCHIVE = "timelapse_archive"      # Zeitraffer nach /media sichern
CONF_ARCHIVE_KEEP = "timelapse_keep"    # so viele neueste auf dem Drucker lassen (0 = nie loeschen)
CONF_MAINTENANCE = "maintenance"        # {"plate": 30, ...} Intervalle in Druckstunden

DEFAULT_PORT = 80
DEFAULT_FILES_LIMIT = 24
DEFAULT_SHUTDOWN_HOST = True
DEFAULT_AUTO_OFF = False
DEFAULT_AUTO_OFF_TEMP = 50
DEFAULT_AUTO_OFF_DELAY = 5  # Minuten
DEFAULT_AUTO_ON = False
NOTIFY_EVENTS = ("complete", "cancelled", "error", "paused", "alert", "first_layer", "almost_done",
                 "spool_low", "spool_runout", "bed_cool")
DEFAULT_NOTIFY_EVENTS = ["complete", "error", "paused", "alert", "spool_low", "spool_runout"]
CONF_BED_COOL = "bed_cool_temp"
DEFAULT_BED_COOL = 35  # °C: PEI-Platte loest das Teil
CONF_IDLE_OFF = "idle_off_hours"
DEFAULT_IDLE_OFF = 0  # 0 = aus
RUNOUT_WARN_MIN = 30  # Spule laeuft in weniger als x min leer -> Push
EVENT_NOTIFY_ACTION = "mobile_app_notification_action"
# Snapmaker veroeffentlicht die Firmware-Quellen mit Commits "Release firmware version x.y.z"
FIRMWARE_REPOS = ("Snapmaker/u1-moonraker", "Snapmaker/u1-klipper")
FIRMWARE_CHECK_S = 24 * 3600
CONF_ALMOST_DONE = "almost_done_minutes"
DEFAULT_ALMOST_DONE = 10  # Minuten vor Ende
CONF_BACKUP = "config_backup"
DEFAULT_BACKUP = True
BACKUP_KEEP = 10
BACKUP_MAX_BYTES = 2 * 1024**2
BACKUP_DIR = "snapmaker_u1_backup"
HISTORY_SIZE = 20
DEFAULT_SPOOLMAN_DEDUCT = True
DEFAULT_SPOOLMAN_LOW = 100  # g
SPOOLMAN_INTERVAL_S = 60
DEFAULT_ARCHIVE = False
DEFAULT_ARCHIVE_KEEP = 5
STATS_INTERVAL_S = 900
UPLOAD_MAX_BYTES = 2 * 1024**3
TIMELAPSE_INTERVAL_S = 300
# Einschalten bis Moonraker/Klipper bereit sind (U1 bootet ca. 1-2 min).
POWER_ON_TIMEOUT_S = 240

# Nach machine.shutdown: warten, bis der Drucker nicht mehr antwortet
# (hoechstens SHUTDOWN_MAX_S), danach noch SHUTDOWN_SETTLE_S fuer das
# Dateisystem, dann Strom aus.
SHUTDOWN_MAX_S = 60
SHUTDOWN_SETTLE_S = 10

EVENT_PRINT_FINISHED = f"{DOMAIN}_print_finished"

UPDATE_INTERVAL = timedelta(seconds=10)
# Live-Abo steht: Abfrage nur noch als Abgleich (live.py)
LIVE_INTERVAL = timedelta(seconds=30)
FILES_INTERVAL = timedelta(seconds=60)

# Karte und Vorschaubilder liefert die Integration selbst aus. Die Pfade
# duerfen nicht ineinander liegen: ein statischer Pfad faengt sonst alle
# Unterpfade ab und die Vorschaubilder liefern 404.
CARD_URL = f"/{DOMAIN}/card"
CARD_FILENAME = "snapmaker-u1-card.js"
THUMB_URL = f"/{DOMAIN}/thumbs"

SERVICE_START_PRINT = "start_print"
SERVICE_REFRESH = "refresh"
SERVICE_POWER_ON = "power_on"
SERVICE_POWER_OFF = "power_off"
SERVICE_SET_SPOOL = "set_spool"
SERVICE_QUEUE_ADD = "queue_add"
SERVICE_QUEUE_REMOVE = "queue_remove"
SERVICE_QUEUE_MOVE = "queue_move"
SERVICE_QUEUE_START = "queue_start"
SERVICE_QUEUE_CLEAR = "queue_clear"
SERVICE_MAINTENANCE_DONE = "maintenance_done"
SERVICE_BACKUP_CONFIG = "backup_config"
SERVICE_BACKUP_TIMELAPSES = "backup_timelapses"

# Zeitraffer laufen ueber einen authentifizierten Proxy der Integration
# (Range-Anfragen fuer den Videoplayer, keine Drucker-IP im Browser).
VIDEO_URL = f"/api/{DOMAIN}/video"
UPLOAD_URL = f"/api/{DOMAIN}/upload"
