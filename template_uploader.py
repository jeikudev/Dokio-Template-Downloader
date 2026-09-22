import os
import re
import sys
import time
import zipfile
import tempfile
import subprocess
from pathlib import Path
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PAGE_WAIT = 15
UPLOAD_WAIT = 120        # wait for presign upload to finish (hidden zip_path populated)
CONFIRM_WAIT = 900       # wait for background processing before confirm screen appears

WELCOME = """
+==============================================================+
|          Dokio Template Uploader Script  v1.0                 |
+==============================================================+
|                                                               |
|  Bulk-uploads new versions of templates into a Dokio hub.     |
|                                                               |
|  What this script does:                                       |
|    - Type a hub name like 'gwm' or 'bupa-agedcare'           |
|    - Pick your browser - it launches with remote debugging    |
|    - Paste the template id(s) you want to upload              |
|    - Paste the folder that holds the template subfolders      |
|    - Reads each template's data.yaml to find its type (mode)  |
|    - Zips each folder (files flat at root) and uploads it     |
|    - Auto-confirms the upload (waits out background jobs)      |
|                                                               |
+==============================================================+
"""

# data.yaml 'mode:' value  ->  admin URL path segment
MODE_TO_SEGMENT = {
    "video": "video_templates",
    "pdf": "pdf_templates",
    "general": "general_templates",
    "email": "email_templates",
    "archive": "archive_templates",
}

BROWSERS = {
    "1": {
        "name": "Google Chrome",
        "binary": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    },
    "2": {
        "name": "Chrome Canary",
        "binary": "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    },
    "3": {
        "name": "Brave",
        "binary": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    },
    "4": {
        "name": "Helium",
        "binary": "/Applications/Helium.app/Contents/MacOS/Helium",
    },
}


def choose_environment():
    print("\nStaging or Production?")
    print("  [1] Production  (e.g. https://gwm.dokio.co)")
    print("  [2] Staging     (e.g. https://gwm.staging.dokio.xyz)")
    while True:
        val = input("\n  Enter number: ").strip()
        if val == "1":
            return "production"
        elif val == "2":
            return "staging"
        print("  Please enter 1 or 2.")


def choose_hub():
    env = choose_environment()

    print("\nWhich Dokio hub?")
    print("  Type the hub name or full URL.")
    print("  Examples: gwm, bupa-agedcare, poolwerx, ipa")
    while True:
        val = input("\n  Hub: ").strip().lower().rstrip("/")
        if not val:
            print("  Please enter a hub name.")
            continue
        if val.startswith("http"):
            val = val.split("//")[1].split(".")[0]
        hub_name = val

        if env == "staging":
            base_url = f"https://{hub_name}.staging.dokio.xyz"
        else:
            base_url = f"https://{hub_name}.dokio.co"

        print(f"  Environment: {env}")
        print(f"  Hub URL    : {base_url}")
        return hub_name, base_url


def choose_browser():
    print("\nWhich browser?")
    for key, info in BROWSERS.items():
        exists = os.path.exists(info["binary"])
        status = "installed" if exists else "not found"
        print(f"  [{key}] {info['name']}  ({status})")
    while True:
        choice = input("\n  Enter number: ").strip()
        if choice in BROWSERS:
            return BROWSERS[choice]
        print(f"  Please enter a valid number (1-{len(BROWSERS)}).")


def choose_ids():
    print("\nWhich template id(s)? (comma-separated)")
    print("  Example: 9H779M, E7D4MC, 7C43DC, JC6RD7")
    while True:
        val = input("\n  Ids: ").strip()
        ids = [p.strip() for p in val.split(",") if p.strip()]
        if ids:
            return ids
        print("  Please enter at least one id.")


def choose_folder():
    print("\nFolder that holds the template subfolders?")
    print("  Example: ~/Documents/Dokio Templates/gwm-templates")
    while True:
        raw = input("\n  Folder path: ").strip()
        # Handle drag-and-drop paths: strip quotes and unescape spaces
        raw = raw.strip('"').strip("'").replace("\\ ", " ")
        path = os.path.expanduser(raw.rstrip("/"))
        if os.path.isdir(path):
            print(f"  Folder: {path}")
            return path
        print(f"  Not a folder: {path}")


def resolve_folder(hub_name):
    """Use the folder the downloader creates for this hub; ask only if missing.

    Downloader saves to ~/Documents/Dokio Templates/<hub>-templates/ - reuse it.
    """
    default_dir = Path.home() / "Documents" / "Dokio Templates" / f"{hub_name}-templates"
    if default_dir.is_dir():
        print(f"\n  Using downloaded folder: {default_dir}")
        return str(default_dir)
    print(f"\n  No downloaded folder at: {default_dir}")
    return choose_folder()


def find_folder(root, template_id):
    """Find the subfolder in root matching template_id.

    Folder names are the bare id ('JC6RD7') or id-with-name ('JC6RD7 - Name').
    The id is always the leading token. Returns the full path or None.
    """
    tid = template_id.lower()
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        if not os.path.isdir(full):
            continue
        name = entry.strip()
        low = name.lower()
        first = name.split()[0].lower() if name.split() else ""
        if low == tid or first == tid or low.startswith(tid + " ") or low.startswith(tid + "-"):
            return full
    return None


def read_mode(folder):
    """Read the 'mode:' value from the folder's data.yaml. Returns lowercased str or None."""
    yaml_path = os.path.join(folder, "data.yaml")
    if not os.path.exists(yaml_path):
        return None
    with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s.lower().startswith("mode:"):
                return s.split(":", 1)[1].strip().strip('"').strip("'").lower()
    return None


def zip_folder_flat(folder, out_zip):
    """Zip the folder's contents with files flat at the archive root (no wrapping dir)."""
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(folder):
            for fname in files:
                if fname == ".DS_Store":
                    continue
                fp = os.path.join(root, fname)
                arc = os.path.relpath(fp, folder)  # relative to folder -> flat root
                z.write(fp, arc)


def is_debug_browser_running():
    """Check if a browser with remote debugging is already running on port 9222."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect(("127.0.0.1", 9222))
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


def launch_browser(browser_info):
    """Launch browser with remote debugging, or skip if one is already running."""
    if is_debug_browser_running():
        print("\n  Debug browser already running on port 9222 - reusing it!")
        print("  (If you need a different browser, close it and re-run.)")
        input("\n  Press Enter to continue...")
        return

    binary = browser_info["binary"]
    name = browser_info["name"]

    if not os.path.exists(binary):
        print(f"\n  {name} not found at: {binary}")
        print(f"  Please launch it manually with: --remote-debugging-port=9222")
        input("  Press Enter once the browser is open and you're logged in via Okta...")
        return

    debug_dir = "/tmp/dokio-debug"
    cmd = [binary, "--remote-debugging-port=9222", f"--user-data-dir={debug_dir}"]

    print(f"\n  Launching {name}...")
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    print(f"  Waiting for {name} to start...")
    time.sleep(4)

    print(f"  {name} should now be open!")
    print(f"\n  In the browser window:")
    print(f"    1. Log in via Okta if needed")
    print(f"    2. Come back to THIS terminal")
    input(f"\n  Press Enter when you're logged in and ready...")


def connect_to_browser():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)
    print(f"  Connected! (page: {driver.title})")
    return driver


def upload_one(driver, base_url, segment, template_id, zip_path):
    """Upload a zip as a new version of one template. Returns True on success."""
    upload_url = f"{base_url}/admin/{segment}/{template_id}/upload"
    driver.get(upload_url)

    wait = WebDriverWait(driver, PAGE_WAIT)

    # Step 1 - drop the zip into the file input; page JS presigns + uploads it.
    file_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
    )
    file_input.send_keys(os.path.abspath(zip_path))

    # Wait for the presign upload to finish (hidden zip_path gets a value).
    zip_path_val = ""
    upload_end = time.time() + UPLOAD_WAIT
    while time.time() < upload_end:
        try:
            el = driver.find_element(By.CSS_SELECTOR, "input[name='zip_path'][type='hidden']")
            zip_path_val = el.get_attribute("value") or ""
        except Exception:
            zip_path_val = ""
        if zip_path_val:
            break
        time.sleep(1)

    if not zip_path_val:
        print("    FAILED: upload did not finish (no zip_path).")
        return False

    # Click Continue -> posts stage_upload.
    try:
        cont = driver.find_element(By.XPATH, "//button[normalize-space()='Continue']")
        cont.click()
    except Exception:
        print("    FAILED: could not find Continue button.")
        return False

    # Step 2 - wait for the confirm screen. Small files land there directly;
    # large files process in the background, then become reachable at validate_upload.
    confirm_btn = None
    encoded = quote(zip_path_val, safe="")
    validate_url = f"{base_url}/admin/{segment}/{template_id}/validate_upload?zip_path={encoded}"
    confirm_end = time.time() + CONFIRM_WAIT
    printed_wait = False
    while time.time() < confirm_end:
        btns = driver.find_elements(By.XPATH, "//button[normalize-space()='Confirm upload']")
        if btns:
            confirm_btn = btns[0]
            break
        # Not ready yet - poke validate_upload (works once the background job is done).
        if not printed_wait:
            print("    Processing in background, waiting for confirm screen...")
            printed_wait = True
        driver.get(validate_url)
        time.sleep(2)
        btns = driver.find_elements(By.XPATH, "//button[normalize-space()='Confirm upload']")
        if btns:
            confirm_btn = btns[0]
            break
        time.sleep(5)

    if not confirm_btn:
        print("    FAILED: confirm screen never appeared (timed out).")
        return False

    # Leave 'Major change?' unchecked. Click Confirm upload - and keep clicking.
    # A single click can no-op if React hasn't wired the handler yet or the
    # button sits under the fixed ConfirmBar / off-screen, so re-find and
    # re-click each pass until the page actually leaves the upload flow.
    done_end = time.time() + 120
    while time.time() < done_end:
        url = driver.current_url
        left_flow = not any(x in url for x in ("/upload", "stage_upload", "validate_upload"))
        btns = driver.find_elements(By.XPATH, "//button[normalize-space()='Confirm upload']")
        if left_flow and not btns:
            print("    Confirmed.")
            return True
        if btns:
            btn = btns[0]
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                btn.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    pass
        time.sleep(3)

    print("    FAILED: confirm did not complete (still on upload screen).")
    return False


def run_jobs(driver, base_url, jobs):
    """Upload each job. Returns (success, failed) as lists of job tuples."""
    success, failed = [], []
    for i, (tid, segment, zip_path) in enumerate(jobs, 1):
        print(f"\n[{i}/{len(jobs)}] {tid}  ({segment})")
        try:
            ok = upload_one(driver, base_url, segment, tid, zip_path)
        except Exception as e:
            print(f"    ERROR: {e}")
            ok = False
        (success if ok else failed).append((tid, segment, zip_path))
    return success, failed


def ask_retry(failed):
    """Show the failed uploads and ask whether to re-upload them or quit."""
    print("\n  Failed uploads:")
    for tid, segment, _ in failed:
        print(f"    - {tid}  ({segment})")
    print("\n  What now?")
    print("  [1] Re-upload failed")
    print("  [2] Quit")
    while True:
        val = input("\n  Enter number: ").strip()
        if val == "1":
            return True
        if val == "2":
            return False
        print("  Please enter 1 or 2.")


def main():
    print(WELCOME)

    hub_name, base_url = choose_hub()
    browser_info = choose_browser()
    ids = choose_ids()
    root = resolve_folder(hub_name)

    # Resolve each id -> (folder, segment) offline before touching the browser.
    tmp_dir = tempfile.mkdtemp(prefix="dokio-upload-")
    jobs = []       # (template_id, segment, zip_path)
    skipped = []    # (template_id, reason)

    print("\nResolving templates...")
    for tid in ids:
        folder = find_folder(root, tid)
        if not folder:
            print(f"  {tid}: no matching folder - skipping")
            skipped.append((tid, "no folder"))
            continue

        mode = read_mode(folder)
        if not mode:
            print(f"  {tid}: no 'mode:' in data.yaml - skipping")
            skipped.append((tid, "no mode"))
            continue

        segment = MODE_TO_SEGMENT.get(mode)
        if not segment:
            print(f"  {tid}: unknown mode '{mode}' - skipping")
            skipped.append((tid, f"unknown mode '{mode}'"))
            continue

        zip_path = os.path.join(tmp_dir, f"{tid}.zip")
        zip_folder_flat(folder, zip_path)
        print(f"  {tid}: {mode} -> {segment}  ({os.path.basename(folder)})")
        jobs.append((tid, segment, zip_path))

    if not jobs:
        print("\nNothing to upload. Check ids and folder path.")
        sys.exit(0)

    print(f"\n" + "-" * 60)
    print(f"  Hub      : {hub_name} ({base_url})")
    print(f"  Browser  : {browser_info['name']}")
    print(f"  To upload: {len(jobs)}   Skipped: {len(skipped)}")
    print("-" * 60)

    launch_browser(browser_info)

    print(f"\nConnecting to browser...")
    try:
        driver = connect_to_browser()
    except Exception as e:
        print(f"\nCould not connect: {e}")
        print("Make sure the browser is open and you're logged in.")
        sys.exit(1)

    all_success, failed = [], []
    try:
        pending = jobs
        while pending:
            success, failed = run_jobs(driver, base_url, pending)
            all_success.extend(success)
            if not failed:
                break
            if not ask_retry(failed):
                break
            print(f"\nRe-uploading {len(failed)} failed template(s)...")
            pending = failed
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    finally:
        print("\n" + "=" * 60)
        print(f"  Uploaded : {len(all_success)}")
        print(f"  Failed   : {len(failed)}")
        print(f"  Skipped  : {len(skipped)}")
        if failed:
            print("\n  Failed:")
            for tid, segment, _ in failed:
                print(f"    - {tid}  ({segment})")
        if skipped:
            print("\n  Skipped:")
            for t, reason in skipped:
                print(f"    - {t} ({reason})")
        print("=" * 60)
        print("\nBrowser window left open. Done!")


if __name__ == "__main__":
    main()
