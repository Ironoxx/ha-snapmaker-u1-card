"""Constants shared across the integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "snapmaker_u1_card"
VERSION = "1.6.0b1"

CONF_API_KEY = "api_key"
CONF_FILES_LIMIT = "files_limit"
CONF_POWER_SWITCH = "power_switch"
CONF_POWER_SENSOR = "power_sensor"
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_ENERGY_PRICE_FIXED = "energy_price_fixed"  # fixed price per kWh (without price entity)
CONF_ENERGY_PRICE = "energy_price"  # Price entity (sensor/input_number)
CONF_AUTO_ON = "auto_on"
CONF_NOTIFY = "notify_targets"
CONF_NOTIFY_EVENTS = "notify_events"
CONF_CAMERA = "camera"
CONF_SPOOLMAN_URL = "spoolman_url"
CONF_SPOOLMAN_DEDUCT = "spoolman_deduct"
CONF_SPOOLMAN_LOW = "spoolman_low"
CONF_FILAMENT_PRICES = "filament_prices"  # {"PLA": 20.0, ...} per kg
CONF_SHUTDOWN_HOST = "shutdown_host"
CONF_AUTO_OFF = "auto_off"
CONF_AUTO_OFF_TEMP = "auto_off_temp"
CONF_AUTO_OFF_DELAY = "auto_off_delay"
CONF_ARCHIVE = "timelapse_archive"      # Back up timelapses to /media
CONF_ARCHIVE_KEEP = "timelapse_keep"    # keep this many newest on the printer (0 = never delete)
# Limits for the backup in the media folder (0 = no limit)
CONF_ARCHIVE_MAX = "timelapse_archive_max"    # newest videos kept
CONF_ARCHIVE_DAYS = "timelapse_archive_days"  # delete backups older than this
CONF_MAINTENANCE = "maintenance"        # {"plate": 30, ...} intervals in print hours

DEFAULT_PORT = 80
DEFAULT_FILES_LIMIT = 24
DEFAULT_SHUTDOWN_HOST = True
DEFAULT_AUTO_OFF = False
DEFAULT_AUTO_OFF_TEMP = 50
DEFAULT_AUTO_OFF_DELAY = 5  # minutes
DEFAULT_AUTO_ON = False
NOTIFY_EVENTS = ("complete", "cancelled", "error", "paused", "alert", "first_layer", "almost_done",
                 "spool_low", "spool_runout", "bed_cool")
DEFAULT_NOTIFY_EVENTS = ["complete", "error", "paused", "alert", "spool_low", "spool_runout"]
CONF_BED_COOL = "bed_cool_temp"
DEFAULT_BED_COOL = 35  # °C: the PEI plate releases the part
CONF_IDLE_OFF = "idle_off_hours"
DEFAULT_IDLE_OFF = 0  # 0 = off
RUNOUT_WARN_MIN = 30  # Spool runs out in less than x min -> push notification
EVENT_NOTIFY_ACTION = "mobile_app_notification_action"
# Snapmaker publishes the firmware sources with commits "Release firmware version x.y.z"
FIRMWARE_REPOS = ("Snapmaker/u1-moonraker", "Snapmaker/u1-klipper")
FIRMWARE_CHECK_S = 24 * 3600
CONF_ALMOST_DONE = "almost_done_minutes"
DEFAULT_ALMOST_DONE = 10  # minutes before the end
CONF_BACKUP = "config_backup"
DEFAULT_BACKUP = True
BACKUP_KEEP = 5
BACKUP_MAX_BYTES = 2 * 1024**2
BACKUP_DIR = "snapmaker_u1_backup"
HISTORY_SIZE = 20
DEFAULT_SPOOLMAN_DEDUCT = True
DEFAULT_SPOOLMAN_LOW = 100  # g
SPOOLMAN_INTERVAL_S = 60
DEFAULT_ARCHIVE = False
DEFAULT_ARCHIVE_KEEP = 5
DEFAULT_ARCHIVE_MAX = 50
DEFAULT_ARCHIVE_DAYS = 0
STATS_INTERVAL_S = 900
UPLOAD_MAX_BYTES = 2 * 1024**3
TIMELAPSE_INTERVAL_S = 300
# Switch-on until Moonraker/Klipper are ready (the U1 boots in about 1-2 min).
POWER_ON_TIMEOUT_S = 240

# After machine.shutdown: wait until the printer stops answering
# (at most SHUTDOWN_MAX_S), then another SHUTDOWN_SETTLE_S for the
# file system, then power off.
SHUTDOWN_MAX_S = 60
SHUTDOWN_SETTLE_S = 10

EVENT_PRINT_FINISHED = f"{DOMAIN}_print_finished"

UPDATE_INTERVAL = timedelta(seconds=10)
# Live subscription is up: polling only as a consistency check (live.py)
LIVE_INTERVAL = timedelta(seconds=30)
FILES_INTERVAL = timedelta(seconds=60)

# The integration serves the card and the thumbnails itself. The paths
# must not be nested: a static path would otherwise swallow all
# sub-paths and the thumbnails would return 404.
CARD_URL = f"/{DOMAIN}/card"
CARD_FILENAME = "snapmaker-u1-card.js"
THUMB_URL = f"/{DOMAIN}/thumbs"

SERVICE_START_PRINT = "start_print"
SERVICE_REFRESH = "refresh"
SERVICE_POWER_ON = "power_on"
SERVICE_POWER_OFF = "power_off"
SERVICE_SET_SPOOL = "set_spool"
SERVICE_SET_PREFERENCE = "set_preference"
SERVICE_SET_FILAMENT = "set_filament"
SERVICE_QUEUE_ADD = "queue_add"
SERVICE_QUEUE_REMOVE = "queue_remove"
SERVICE_QUEUE_MOVE = "queue_move"
SERVICE_QUEUE_START = "queue_start"
SERVICE_QUEUE_CLEAR = "queue_clear"
SERVICE_MAINTENANCE_DONE = "maintenance_done"
SERVICE_BACKUP_CONFIG = "backup_config"
SERVICE_BACKUP_TIMELAPSES = "backup_timelapses"

# Timelapses go through an authenticated proxy of the integration
# (Range requests for the video player, no printer IP in the browser).
VIDEO_URL = f"/api/{DOMAIN}/video"
GCODE_URL = f"/api/{DOMAIN}/gcode"
UPLOAD_URL = f"/api/{DOMAIN}/upload"

# Keep Snapmaker's camera service streaming (camera.start_monitor): off | printing | always.
# Stock firmware stops the camera after a while; modified firmware usually does not need it.
CONF_LIVE_BUDGET = "live_notify_budget"
CONF_LIVE_IMAGE = "live_notify_image"
DEFAULT_LIVE_IMAGE = True
# Tapping a notification opens this path/URL (e.g. /dashboard-drucker/0)
CONF_NOTIFY_URL = "notify_click_url"
DEFAULT_LIVE_BUDGET = 150  # progress updates per day and device
CONF_CAMERA_WAKE = "camera_wake"
CAMERA_WAKE_MODES = ("off", "printing", "always")
DEFAULT_CAMERA_WAKE = "off"
CAMERA_WAKE_S = 10
