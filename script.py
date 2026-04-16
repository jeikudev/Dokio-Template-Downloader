import os
import sys
import time
import shutil
import zipfile
import subprocess
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PAGE_WAIT = 15

WELCOME = """
+==============================================================+
|          Dokio Template Downloader Script  v3.0               |
+==============================================================+
|                                                               |
|  Because Jake is too lazy to click through 300+ templates     |
|  across 50+ hubs manually.                                    |
|                                                               |
|  What this script does:                                       |
|    - Type a hub name like 'bupa-sam' or 'poolwerx'            |
|    - Pick your browser (Chrome, Firefox, Brave)               |
|    - Auto-launches browser with remote debugging              |
|    - Scans ALL pages of templates automatically               |
|    - Skips Static PDF and Archive templates                   |
|    - Downloads, unzips into properly named folders            |
|    - Folder named: 746K64 - Template Name                     |
|    - Files inside keep their original names                   |
|                                                               |
|  Auto-saves to: ~/Documents/<hub-name>-templates/             |
|                                                               |
+==============================================================+
"""

BROWSERS = {
    "1": {
        "name": "Google Chrome",
        "binary": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "type": "chrome",
    },
    "2": {
        "name": "Chrome Canary",
        "binary": "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "type": "chrome",
    },
    "3": {
        "name": "Brave",
        "binary": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "type": "chrome",
    },
    "4": {
        "name": "Firefox",
        "binary": "/Applications/Firefox.app/Contents/MacOS/firefox",
        "type": "firefox",
    },
}


def choose_hub():
    print("\nWhich Dokio hub?")
    print("  Type the hub name or full URL.")
    print("  Examples: bupa-sam, poolwerx, ipa, australian-unity")
    print("  Or: https://bupa-sam.dokio.co")
    while True:
        val = input("\n  Hub: ").strip().lower().rstrip("/")
        if not val:
            print("  Please enter a hub name.")
            continue
        # Extract subdomain if full URL pasted
        if val.startswith("http"):
            val = val.split("//")[1].split(".")[0]
        hub_name = val
        base_url = f"https://{hub_name}.dokio.co"
        templates_url = f"{base_url}/admin/templates"
        download_dir = str(Path.home() / "Documents" / f"{hub_name}-templates")
        os.makedirs(download_dir, exist_ok=True)
        print(f"  Hub URL    : {base_url}")
        print(f"  Save to    : {download_dir}")
        return hub_name, base_url, templates_url, download_dir


def choose_browser():
    print("\nWhich browser?")
    for key, info in BROWSERS.items():
        exists = os.path.exists(info["binary"])
        status = "installed" if exists else "not found"
        print(f"  [{key}] {info['name']}  ({status})")

    while True:
        choice = input("\n  Enter number: ").strip()
        if choice in BROWSERS:
            info = BROWSERS[choice]
            return info
        print("  Please enter a valid number (1-4).")


def launch_browser_remote(browser_info):
    """Launch browser with remote debugging in a separate terminal."""
    binary = browser_info["binary"]
    name = browser_info["name"]

    if not os.path.exists(binary):
        print(f"\n  {name} not found at: {binary}")
        print(f"  Please launch it manually with: --remote-debugging-port=9222")
        input("  Press Enter once the browser is open and you're logged in via Okta...")
        return None

    debug_dir = "/tmp/dokio-debug"

    if browser_info["type"] == "firefox":
        cmd = f'"{binary}" --remote-debugging-port 9222 --profile {debug_dir}'
    else:
        cmd = f'"{binary}" --remote-debugging-port=9222 --user-data-dir="{debug_dir}"'

    # Launch in a new Terminal window via AppleScript
    applescript = f'''
    tell application "Terminal"
        activate
        do script "{cmd}"
    end tell
    '''

    print(f"\n  Launching {name} with remote debugging...")
    subprocess.run(["osascript", "-e", applescript], capture_output=True)

    print(f"  A new Terminal window opened running {name}.")
    print(f"\n  Now in that browser window:")
    print(f"    1. Log in via Okta if needed")
    print(f"    2. Come back to THIS terminal")
    input(f"\n  Press Enter when you're logged in and ready...")
    return True


def connect_to_browser(browser_info, download_dir):
    if browser_info["type"] == "firefox":
        options = FirefoxOptions()
        options.add_argument("--remote-debugging-port=9222")
        if os.path.exists(browser_info["binary"]):
            options.binary_location = browser_info["binary"]
        driver = webdriver.Firefox(options=options)
    else:
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        if os.path.exists(browser_info["binary"]):
            options.binary_location = browser_info["binary"]
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(options=options)

    print(f"  Connected to {browser_info['name']}!")
    return driver


def sanitize_filename(name):
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


def get_session(driver, base_url):
    session = requests.Session()
    driver.get(base_url)
    time.sleep(1)
    for c in driver.get_cookies():
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
    session.headers.update({
        "User-Agent": driver.execute_script("return navigator.userAgent"),
        "Referer": base_url,
    })
    return session


def collect_all_templates(driver, templates_url):
    all_templates = []
    page = 1

    while True:
        url = f"{templates_url}?page={page}"
        print(f"  Scanning page {page}...")
        driver.get(url)

        try:
            WebDriverWait(driver, PAGE_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.AdminListRow"))
            )
        except Exception:
            if page == 1:
                print(f"  No templates found on page 1.")
            else:
                print(f"  No more rows at page {page}. Done scanning.")
            break

        time.sleep(1)
        rows = driver.find_elements(By.CSS_SELECTOR, "div.AdminListRow")
        if not rows:
            break

        added, skipped = 0, 0
        for row in rows:
            try:
                title_el = row.find_element(By.CSS_SELECTOR, "a._title")
                name = title_el.text.strip()
                detail_url = title_el.get_attribute("href")
                if not name or not detail_url:
                    continue

                try:
                    details_els = row.find_elements(By.CSS_SELECTOR, "div[class*='_column']")
                    details_text = " ".join(el.text for el in details_els).lower()
                except Exception:
                    details_text = ""

                if "static" in details_text or "archive" in details_text:
                    skipped += 1
                    continue

                download_url = detail_url.rstrip("/") + "/download"
                dokio_id = detail_url.rstrip("/").split("/")[-1]
                display_name = f"{dokio_id} - {name}"
                all_templates.append((display_name, download_url))
                added += 1
            except Exception:
                continue

        print(f"    {added} added, {skipped} skipped (Static/Archive)")

        try:
            driver.find_element(By.XPATH, f"//a[contains(@href,'page={page + 1}')]")
            page += 1
        except Exception:
            print(f"  No more pages. Done.")
            break

    print(f"\n  Total: {len(all_templates)} templates across {page} page(s).")
    return all_templates


def handle_file(original_path, safe_name, download_dir):
    """Unzip into a named folder. Keep original filenames inside."""
    ext = Path(original_path).suffix.lower()

    if ext == ".zip":
        extract_dir = os.path.join(download_dir, safe_name)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(original_path, "r") as z:
            z.extractall(extract_dir)

        # List what was extracted (keep original names, don't rename)
        extracted = [f for f in os.listdir(extract_dir)
                     if os.path.isfile(os.path.join(extract_dir, f))]
        for fname in extracted:
            print(f"    {fname}")

        os.remove(original_path)
        print(f"    -> {len(extracted)} file(s) in {safe_name}/")
    else:
        # Single file, not a zip - put it in a named folder too
        folder = os.path.join(download_dir, safe_name)
        os.makedirs(folder, exist_ok=True)

        # Keep original filename from Content-Disposition if we have it,
        # otherwise use whatever name the tmp file has
        original_name = Path(original_path).name.replace(f"_tmp_{safe_name}", "")
        if not original_name or original_name == ext:
            original_name = f"file{ext}"
        dest = os.path.join(folder, original_name)
        shutil.move(original_path, dest)
        print(f"    {original_name}")
        print(f"    -> 1 file in {safe_name}/")


def download_all(driver, session, templates, download_dir):
    success, failed = [], []

    for i, (name, download_url) in enumerate(templates, 1):
        print(f"\n[{i}/{len(templates)}] {name}")
        safe_name = sanitize_filename(name)

        try:
            response = session.get(download_url, stream=True, timeout=60)

            if response.status_code == 401:
                print(f"  FAILED: Session expired. Re-login in browser and restart.")
                failed.append(name)
                continue
            elif response.status_code != 200:
                print(f"  FAILED: HTTP {response.status_code}")
                failed.append(name)
                continue

            # Determine extension from response
            ext = ".zip"
            original_filename = None
            cd = response.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                original_filename = cd.split("filename=")[-1].strip().strip('"').strip("'")
                ext = Path(original_filename).suffix or ext
            elif "application/pdf" in response.headers.get("Content-Type", ""):
                ext = ".pdf"

            tmp_path = os.path.join(download_dir, f"_tmp_{safe_name}{ext}")
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            handle_file(tmp_path, safe_name, download_dir)
            success.append(name)

        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append(name)

    print("\n" + "=" * 60)
    print(f"  Downloaded : {len(success)}")
    print(f"  Failed     : {len(failed)}")
    if failed:
        print("\n  Failed templates:")
        for f in failed:
            print(f"    - {f}")
    print(f"\n  Files saved to: {download_dir}")
    print("=" * 60)


if __name__ == "__main__":
    print(WELCOME)

    # 1. Ask hub name
    hub_name, base_url, templates_url, download_dir = choose_hub()

    # 2. Ask browser
    browser_info = choose_browser()

    # Summary
    print(f"\n" + "-" * 60)
    print(f"  Hub      : {hub_name} ({base_url})")
    print(f"  Browser  : {browser_info['name']}")
    print(f"  Save to  : {download_dir}")
    print("-" * 60)

    # 3. Auto-launch browser with remote debugging
    launch_browser_remote(browser_info)

    # 4. Connect
    print(f"\nConnecting to {browser_info['name']}...")
    try:
        driver = connect_to_browser(browser_info, download_dir)
    except Exception as e:
        print(f"\nCould not connect: {e}")
        print("Make sure the browser is open and you're logged in.")
        sys.exit(1)

    try:
        print(f"\nScanning templates at {templates_url}...")
        templates = collect_all_templates(driver, templates_url)

        if not templates:
            print("No templates found. Check hub name and make sure you're logged in.")
            sys.exit(0)

        print(f"\nGrabbing session cookies...")
        session = get_session(driver, base_url)

        print(f"\nStarting downloads...\n")
        download_all(driver, session, templates, download_dir)

    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    finally:
        print("\nBrowser window left open. Done!")
