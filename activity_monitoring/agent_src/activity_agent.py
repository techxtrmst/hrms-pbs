import json
import os
import subprocess
import sys
import time
from datetime import datetime

import requests

# Suppress subprocess console windows on Windows
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# Platform-specific imports
try:
    if sys.platform == "win32":
        import winreg

        import psutil
        import uiautomation as auto
        import win32api
        import win32console
        import win32gui
        import win32process
    elif sys.platform == "darwin":
        import psutil
except ImportError:
    pass  # Bundled in EXE

# ──────────────────────────────────────────────
#  CONFIGURATION  (overwritten by config.json)
# ──────────────────────────────────────────────
SERVER_URL = "https://petabytzglobal.com/activity-tracking/api/sync/"
API_TOKEN = ""
APP_NAME = "HRMS_Activity_Tracker"

# Resolve the directory this EXE / script lives in
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(BASE_DIR, "config.json")
if os.path.exists(config_path):
    try:
        with open(config_path) as f:
            cfg = json.load(f)
            SERVER_URL = cfg.get("server_url", SERVER_URL)
            API_TOKEN = cfg.get("api_token", API_TOKEN)
    except Exception:
        pass


# ──────────────────────────────────────────────
#  PERSISTENCE
# ──────────────────────────────────────────────
def set_persistence():
    """
    Register the EXE in the Windows startup registry so it runs
    automatically after every restart / shutdown.
    We always register the INSTALLED path (BASE_DIR) not the current path.
    """
    try:
        if sys.platform != "win32":
            return
        # The EXE is installed to %LOCALAPPDATA%\PetaBytz-Tracker\
        exe_path = os.path.join(BASE_DIR, "Pbssys.exe")
        if not os.path.isfile(exe_path):
            # Fallback: use current executable
            exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.SetValueEx(reg_key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
    except Exception:
        pass


def hide_console():
    if sys.platform == "win32":
        try:
            window = win32console.GetConsoleWindow()
            if window:
                win32gui.ShowWindow(window, 0)  # SW_HIDE
        except Exception:
            pass


# ──────────────────────────────────────────────
#  BROWSER / APP TRACKING
# ──────────────────────────────────────────────
def get_browser_url(app_name):
    """Deep-extract the current URL using UI Automation."""
    if sys.platform != "win32":
        return None
    app_lower = app_name.lower()
    if not any(b in app_lower for b in ["chrome", "msedge", "firefox", "brave"]):
        return None
    try:
        browser = auto.WindowControl(ClassName="Chrome_WidgetWin_1", NameRe=".*(Google Chrome|Microsoft Edge|Brave).*")
        if not browser.Exists(0):
            browser = auto.WindowControl(ClassName="MozillaWindowClass")
        if not browser.Exists(0):
            return None
        address_bar = browser.EditControl(Name="Address and search bar")
        if not address_bar.Exists(0):
            address_bar = browser.EditControl(Name="App")
        if address_bar.Exists(0):
            url = address_bar.GetValuePattern().Value
            if url and not url.startswith("http"):
                url = "https://" + url
            return url
    except Exception:
        pass
    return None


def parse_search_query(title, app_name, url=None):
    if url and "google.com/search?q=" in url:
        import urllib.parse

        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q", [None])[0]
        if query:
            return query, "https://google.com"
    app_lower = app_name.lower()
    if any(b in app_lower for b in ["chrome", "edge", "firefox", "brave", "opera"]):
        if " - Google Search" in title:
            return title.replace(" - Google Search", ""), "https://google.com"
        if " - Bing" in title:
            return title.replace(" - Bing", ""), "https://bing.com"
    return None, None


def get_active_window_info():
    if sys.platform == "win32":
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            _, pid = win32process.GetWindowThreadProcessId(window)
            process = psutil.Process(pid)
            app_name = process.name()

            title_lower = title.lower()
            private_keywords = ["incognito", "inprivate", "private browsing", "private window"]
            if any(k in title_lower for k in private_keywords):
                app_name += " [PRIVATE]"

            return app_name, title
        except Exception:
            pass
    return "Unknown", "Unknown"


def capture_screenshot():
    """Capture screen and return as base64 encoded JPG."""
    if sys.platform != "win32":
        return None
    try:
        from io import BytesIO

        from PIL import ImageGrab

        # Capture full screen
        screenshot = ImageGrab.grab()

        # Convert to RGB if necessary
        if screenshot.mode in ("RGBA", "P"):
            screenshot = screenshot.convert("RGB")

        # Resize to 720p to save bandwidth while keeping detail
        screenshot.thumbnail((1280, 720))

        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=40)  # High compression for speed

        import base64

        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        # Don't fail the agent if capture fails
        error_log = os.path.join(BASE_DIR, "sync_errors.log")
        with open(error_log, "a") as f:
            f.write(f"{datetime.now()}: Screenshot failed - {str(e)}\n")
        return None


def get_idle_time():
    if sys.platform != "win32":
        return 0
    try:
        last_input = win32api.GetLastInputInfo()
        current_tick = win32api.GetTickCount()
        return (current_tick - last_input) / 1000
    except Exception:
        return 0


# ──────────────────────────────────────────────
#  USB / FILE-TRANSFER TRACKING
# ──────────────────────────────────────────────
def _get_usb_devices():
    """
    Use PowerShell to list all present USB PnP devices.
    Returns a dict  {device_id: friendly_name}
    """
    # Use pipeline-style syntax that works in both PS5 and PS7
    ps_cmd = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object InstanceId -like 'USB*' | "
        "Select-Object InstanceId, FriendlyName | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    try:
        raw = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            timeout=10,
            creationflags=_SUBPROCESS_FLAGS,  # NO popup window!
        ).decode(errors="ignore")

        devices = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith('"InstanceId"'):
                continue  # skip header
            parts = line.split('","')
            if len(parts) >= 2:
                dev_id = parts[0].strip('"')
                name = parts[1].strip('"') or "USB Device"
                if dev_id:
                    devices[dev_id] = name
        return devices
    except Exception:
        return {}


def track_usb_devices(last_device_ids):
    """Compare current USB PnP snapshot with the previous one."""
    events = []
    try:
        current_devices = _get_usb_devices()
        current_ids = set(current_devices.keys())

        added = current_ids - last_device_ids
        removed = last_device_ids - current_ids

        for dev_id in added:
            name = current_devices.get(dev_id, "USB Device")
            events.append(
                {
                    "event_type": "USB_INSERT",
                    "description": f"Hardware connected: {name}",
                    "metadata": {"device_id": dev_id, "name": name},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        for dev_id in removed:
            events.append(
                {
                    "event_type": "USB_REMOVE",
                    "description": f"Hardware disconnected (ID: {dev_id[:40]}...)",
                    "metadata": {"device_id": dev_id},
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return events, current_ids
    except Exception:
        return [], last_device_ids


def _get_removable_drive_files(drive):
    """List files (with mtime + size) in root of given drive."""
    result = {}
    try:
        for f in os.listdir(drive):
            full = os.path.join(drive, f)
            if os.path.isfile(full):
                s = os.stat(full)
                result[f] = (s.st_mtime, s.st_size)
    except Exception:
        pass
    return result


def track_file_transfers(last_file_state):
    """
    Detect files COPIED TO or MODIFIED ON removable USB drives.
    last_file_state: {drive: {filename: (mtime, size)}}
    Returns (events, new_file_state)
    """
    events = []
    new_state = {}

    try:
        removable = [p.device for p in psutil.disk_partitions(all=False) if "removable" in p.opts.lower()]
    except Exception:
        removable = []

    for drive in removable:
        current_files = _get_removable_drive_files(drive)
        new_state[drive] = current_files

        old_files = last_file_state.get(drive, {})

        for fname, (mtime, size) in current_files.items():
            if fname not in old_files:
                events.append(
                    {
                        "event_type": "FILE_TRANSFER",
                        "description": f"File COPIED to USB {drive}: {fname}",
                        "metadata": {"file": fname, "drive": drive, "size": size, "action": "CREATE"},
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            elif old_files[fname] != (mtime, size):
                events.append(
                    {
                        "event_type": "FILE_TRANSFER",
                        "description": f"File MODIFIED on USB {drive}: {fname}",
                        "metadata": {"file": fname, "drive": drive, "size": size, "action": "MODIFY"},
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    return events, new_state


# ──────────────────────────────────────────────
#  DATA SYNC
# ──────────────────────────────────────────────
def sync_data(app_data, browser_data, system_events=None, is_idle=False, idle_seconds=0):
    if system_events is None:
        system_events = []
    payload = {
        "app_activities": app_data,
        "browser_activities": browser_data,
        "system_events": system_events,
        "is_idle": is_idle,
        "idle_seconds": idle_seconds,
    }
    headers = {"Authorization": f"Token {API_TOKEN}", "Content-Type": "application/json"}
    try:
        resp = requests.post(SERVER_URL, json=payload, headers=headers, timeout=15)

        # Log the response for debugging
        if resp.status_code == 201:
            return True
        else:
            # Write error to a log file for debugging
            error_log = os.path.join(BASE_DIR, "sync_errors.log")
            with open(error_log, "a") as f:
                f.write(f"{datetime.now()}: Status {resp.status_code}, Response: {resp.text}\n")
            return False
    except requests.exceptions.ConnectionError as e:
        # Network connection error
        error_log = os.path.join(BASE_DIR, "sync_errors.log")
        with open(error_log, "a") as f:
            f.write(f"{datetime.now()}: Connection Error - {str(e)}\n")
            f.write(f"  Server URL: {SERVER_URL}\n")
        return False
    except Exception as e:
        # Other errors
        error_log = os.path.join(BASE_DIR, "sync_errors.log")
        with open(error_log, "a") as f:
            f.write(f"{datetime.now()}: Error - {str(e)}\n")
        return False


# ──────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────
def main():
    # Register persistence FIRST so even the first run survives a restart
    set_persistence()

    # Send an initial ping so the server knows we're alive
    sync_data([], [], [])

    time.sleep(3)
    hide_console()  # hide after init

    batch_apps = []
    batch_browser = []
    batch_events = []
    batch_screenshots = []
    last_sync = time.time()

    # Next screenshot time initialized to NOW for immediate first capture

    next_screenshot_time = time.time()

    # ── Initialise USB snapshot & log ALL currently-connected devices ──
    initial_devices = _get_usb_devices()
    current_usb_ids = set(initial_devices.keys())

    # Report every device that is ALREADY connected when the tracker starts.
    # This ensures the mouse and other pre-plugged devices appear in the dashboard.
    for dev_id, name in initial_devices.items():
        batch_events.append(
            {
                "event_type": "USB_INSERT",
                "description": f"Hardware present at startup: {name}",
                "metadata": {"device_id": dev_id, "name": name, "startup": True},
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    # ── Initialise file state for removable drives ──
    _, monitored_files = track_file_transfers({})

    while True:
        try:
            idle_seconds = get_idle_time()
            is_idle = idle_seconds > 60

            # 1. Active window (Fixed: returns only 2 values)
            app_name, title = get_active_window_info()

            # 2. Extract URL and Search details for Browsers
            url = get_browser_url(app_name)
            search_query, domain = parse_search_query(title, app_name, url)

            start_time = datetime.utcnow().isoformat() + "Z"

            # 3. USB device changes
            usb_events, current_usb_ids = track_usb_devices(current_usb_ids)
            batch_events.extend(usb_events)

            # 4. File transfers on removable drives
            file_events, monitored_files = track_file_transfers(monitored_files)
            batch_events.extend(file_events)

            time.sleep(10)
            end_time = datetime.utcnow().isoformat() + "Z"

            if not is_idle:
                batch_apps.append(
                    {
                        "app_name": app_name,
                        "window_title": title,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": "00:00:10",
                        "is_productive": ("youtube" not in title.lower() and "meta" not in title.lower()),
                    }
                )
                if search_query or domain:
                    batch_browser.append(
                        {
                            "url": domain or "https://google.com",
                            "title": title,
                            "search_query": search_query or "",
                            "timestamp": start_time,
                            "time_spent": "00:00:10",
                        }
                    )

            # Limit local batches to prevent memory overflow if server is down
            if len(batch_apps) > 500:
                batch_apps = batch_apps[-500:]
            if len(batch_browser) > 500:
                batch_browser = batch_browser[-500:]
            if len(batch_events) > 200:
                batch_events = batch_events[-200:]

            # 4. Periodic Screenshots (TeamLogger style)
            if time.time() > next_screenshot_time:
                shot_b64 = capture_screenshot()
                if shot_b64:
                    batch_screenshots.append({"image_base64": shot_b64, "window_name": f"{app_name} - {title}"[:255]})
                # Set next capture time (exactly 10 minutes)
                next_screenshot_time = time.time() + 600

            # Sync every 60 seconds
            if time.time() - last_sync > 60:
                payload = {
                    "app_activities": batch_apps,
                    "browser_activities": batch_browser,
                    "system_events": batch_events,
                    "screenshots": batch_screenshots,
                    "is_idle": is_idle,
                    "idle_seconds": int(idle_seconds),
                    "agent_version": "2.0-TL",
                }

                headers = {"Content-Type": "application/json", "X-Computer-User": os.getlogin()}
                try:
                    # Robust sync using ?token= for production compatibility
                    url = f"{SERVER_URL}?token={API_TOKEN}"
                    resp = requests.post(url, json=payload, headers=headers, timeout=25)
                    if resp.status_code in [201, 200]:
                        batch_apps = []
                        batch_browser = []
                        batch_events = []
                        batch_screenshots = []
                        last_sync = time.time()
                    else:
                        time.sleep(10)
                except Exception:
                    time.sleep(30)

        except Exception:
            time.sleep(10)  # avoid hard-crash loop


if __name__ == "__main__":
    if API_TOKEN:
        main()
