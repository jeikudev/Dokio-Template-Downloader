import os
import sys
import time
import subprocess
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
|       Dokio GitHub Folder Name Updater Script  v1.0           |
+==============================================================+
|                                                               |
|  Because Jake is STILL too lazy.                              |
|                                                               |
|  What this script does:                                       |
|    - Scans all template pages on a Dokio hub                  |
|    - Opens each template's Edit Settings page                 |
|    - Fills in the 'GitHub repo folder' field with the         |
|      correct folder name: DokioID - Template Name             |
|    - Clicks 'Update' to save                                  |
|    - Skips Static PDF and Archive templates                   |
|    - Skips templates that already have a folder name set      |
|                                                               |
|  Example folder name it sets:                                 |
|    Q33D3U - Hyperlocal Email 2025 - with mask 190326          |
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
    while True:
        val = input("\n  Hub: ").strip().lower().rstrip("/")
        if not val:
            print("  Please enter a hub name.")
            continue
        if val.startswith("http"):
            val = val.split("//")[1].split(".")[0]
        hub_name = val
        base_url = f"https://{hub_name}.dokio.co"
        templates_url = f"{base_url}/admin/templates"
        print(f"  Hub URL    : {base_url}")
        return hub_name, base_url, templates_url


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
        print("  Please enter a valid number (1-4).")


def launch_browser_remote(browser_info):
    binary = browser_info["binary"]
    name = browser_info["name"]

    if not os.path.exists(binary):
        print(f"\n  {name} not found at: {binary}")
        print(f"  Please launch it manually with: --remote-debugging-port=9222")
        input("  Press Enter once the browser is open and you're logged in via Okta...")
        return None

    debug_dir = "/tmp/dokio-debug"

    if browser_info["type"] == "firefox":
        cmd = [binary, "--remote-debugging-port", "9222", "--profile", debug_dir]
    else:
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
    return True


def connect_to_browser(browser_info):
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
        driver = webdriver.Chrome(options=options)

    print(f"  Connected to {browser_info['name']}!")
    return driver


def sanitize_folder_name(name):
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


def collect_all_templates(driver, templates_url):
    """Collect template name, ID, and edit settings URL from all pages."""
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

                # Skip Static PDF and Archive
                try:
                    details_els = row.find_elements(By.CSS_SELECTOR, "div[class*='_column']")
                    details_text = " ".join(el.text for el in details_els).lower()
                except Exception:
                    details_text = ""

                if "static" in details_text or "archive" in details_text:
                    skipped += 1
                    continue

                # Build edit settings URL: /admin/email_templates/Q33D3U -> /admin/email_templates/Q33D3U/edit
                edit_url = detail_url.rstrip("/") + "/edit"
                dokio_id = detail_url.rstrip("/").split("/")[-1]
                folder_name = sanitize_folder_name(f"{dokio_id} - {name}")

                all_templates.append({
                    "name": name,
                    "dokio_id": dokio_id,
                    "folder_name": folder_name,
                    "edit_url": edit_url,
                })
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


def update_github_folder(driver, template):
    """Go to edit settings page, fill GitHub folder, and save."""
    name = template["name"]
    folder_name = template["folder_name"]
    edit_url = template["edit_url"]

    driver.get(edit_url)

    # Wait for the page to load
    try:
        WebDriverWait(driver, PAGE_WAIT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[id*='github_repo_folder']"))
        )
    except Exception:
        # Try alternative: look for input by name attribute
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name*='github_repo_folder']"))
            )
        except Exception:
            print(f"    Could not find GitHub folder input on edit page")
            return False

    time.sleep(0.5)

    # Find the GitHub repo folder input
    github_input = None
    selectors = [
        "input[id*='github_repo_folder']",
        "input[name*='github_repo_folder']",
        "input[name*='[github_repo_folder]']",
    ]
    for sel in selectors:
        try:
            github_input = driver.find_element(By.CSS_SELECTOR, sel)
            if github_input:
                break
        except Exception:
            continue

    if not github_input:
        print(f"    Could not find GitHub folder input")
        return False

    # Check if already filled
    current_value = github_input.get_attribute("value").strip()
    if current_value:
        print(f"    Already set: {current_value} (skipping)")
        return "skipped"

    # Clear and fill in the folder name
    github_input.clear()
    github_input.send_keys(folder_name)
    time.sleep(0.3)

    # Verify it was entered
    entered = github_input.get_attribute("value")
    if entered != folder_name:
        print(f"    Input mismatch! Expected: {folder_name}, Got: {entered}")
        return False

    # Click the Update/Save button
    save_btn = None
    save_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "a.Button._type_primary",
        "button._type_primary",
    ]
    for sel in save_selectors:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                btn_text = btn.text.strip().lower()
                if "update" in btn_text or "save" in btn_text:
                    save_btn = btn
                    break
            if save_btn:
                break
        except Exception:
            continue

    # Also try finding by text content
    if not save_btn:
        try:
            save_btn = driver.find_element(
                By.XPATH, "//button[contains(text(),'Update')] | //input[@value='Update'] | //a[contains(text(),'Update')]"
            )
        except Exception:
            pass

    if not save_btn:
        print(f"    Could not find Save/Update button")
        return False

    save_btn.click()
    time.sleep(1.5)

    print(f"    Set to: {folder_name}")
    return True


def update_all(driver, templates):
    updated, skipped, failed = [], [], []

    for i, t in enumerate(templates, 1):
        print(f"\n[{i}/{len(templates)}] {t['dokio_id']} - {t['name']}")

        try:
            result = update_github_folder(driver, t)
            if result == "skipped":
                skipped.append(t["name"])
            elif result:
                updated.append(t["name"])
            else:
                failed.append(t["name"])
        except Exception as e:
            print(f"    ERROR: {e}")
            failed.append(t["name"])

    print("\n" + "=" * 60)
    print(f"  Updated  : {len(updated)}")
    print(f"  Skipped  : {len(skipped)} (already had a value)")
    print(f"  Failed   : {len(failed)}")
    if failed:
        print("\n  Failed templates:")
        for f in failed:
            print(f"    - {f}")
    print("=" * 60)


if __name__ == "__main__":
    print(WELCOME)

    hub_name, base_url, templates_url = choose_hub()
    browser_info = choose_browser()

    print(f"\n" + "-" * 60)
    print(f"  Hub      : {hub_name} ({base_url})")
    print(f"  Browser  : {browser_info['name']}")
    print("-" * 60)

    launch_browser_remote(browser_info)

    print(f"\nConnecting to {browser_info['name']}...")
    try:
        driver = connect_to_browser(browser_info)
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

        confirm = input(f"\nReady to update {len(templates)} templates. Continue? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            sys.exit(0)

        print(f"\nUpdating GitHub folder names...\n")
        update_all(driver, templates)

    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    finally:
        print("\nBrowser window left open. Done!")