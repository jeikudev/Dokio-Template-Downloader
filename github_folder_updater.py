import os
import sys
import time
import socket
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
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
|    - Connects to the browser opened by the downloader script  |
|    - Scans all template pages on a Dokio hub                  |
|    - Opens each template's Edit Settings page                 |
|    - Fills in the 'GitHub repo folder' field with:            |
|      DokioID - Template Name                                  |
|    - Clicks 'Update' to save                                  |
|    - Skips Static PDF and Archive templates                   |
|    - Skips templates that already have a folder name set       |
|                                                               |
|  NOTE: Run template_downloader.py first! This script reuses   |
|  the same browser window (no need to open a new one).         |
|                                                               |
+==============================================================+
"""


def choose_environment():
    print("\nStaging or Production?")
    print("  [1] Production  (e.g. https://poolwerx.dokio.co)")
    print("  [2] Staging     (e.g. https://poolwerx.staging.dokio.xyz)")
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
    print("  Examples: bupa-sam, poolwerx, ipa, australian-unity")
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

        templates_url = f"{base_url}/admin/templates"
        print(f"  Environment: {env}")
        print(f"  Hub URL    : {base_url}")
        return hub_name, base_url, templates_url


def check_debug_browser():
    """Check if a debug browser is running on port 9222."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect(("127.0.0.1", 9222))
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


def connect_to_browser():
    """Connect to the already-open debug browser from the downloader script."""
    if not check_debug_browser():
        print("\n  No debug browser found on port 9222!")
        print("\n  Run template_downloader.py first — it opens the browser for you.")
        print("  Or launch your browser manually with:")
        print('    --remote-debugging-port=9222 --user-data-dir=/tmp/dokio-debug')
        input("\n  Press Enter once the browser is open, or Ctrl+C to quit...")

        if not check_debug_browser():
            print("\n  Still can't find a debug browser. Exiting.")
            sys.exit(1)

    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)
    print(f"  Connected to browser! (page: {driver.title})")
    return driver


def clean_template_name(name):
    """Remove WIP markers like *WIP*, _WIP_, WIP, (WIP), [WIP] from the name."""
    import re
    name = re.sub(r'[\*_\(\[\s]*WIP[\*_\)\]\s]*', ' ', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'^[\s\-]+|[\s\-]+$', '', name)
    name = re.sub(r'\s*-\s*-\s*', ' - ', name)
    return name.strip()


def sanitize_folder_name(name):
    name = clean_template_name(name)
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


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


def find_github_input(driver):
    """Find the GitHub repo folder input using multiple strategies."""
    # Strategy 1: CSS selectors for known patterns
    css_selectors = [
        "input[id*='github_repo_folder']",
        "input[name*='github_repo_folder']",
        "input[name*='[github_repo_folder]']",
    ]
    for sel in css_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                return els[0]
        except Exception:
            continue

    # Strategy 2: Find by nearby label text "GitHub repo folder"
    try:
        labels = driver.find_elements(By.XPATH,
            "//*[contains(text(),'GitHub repo folder') or contains(text(),'GitHub Repo Folder')]"
        )
        for label in labels:
            # Look for input in the same container
            parent = label.find_element(By.XPATH, "./ancestor::div[contains(@class,'Container') or contains(@class,'Column') or contains(@class,'Field')]")
            inputs = parent.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if inp.get_attribute("type") in ["text", "", None]:
                    return inp
    except Exception:
        pass

    # Strategy 3: JavaScript - find all text inputs and match by name/id
    try:
        result = driver.execute_script("""
            var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
            for (var i = 0; i < inputs.length; i++) {
                var name = (inputs[i].name || '').toLowerCase();
                var id = (inputs[i].id || '').toLowerCase();
                if (name.includes('github') || id.includes('github')) {
                    return inputs[i];
                }
            }
            return null;
        """)
        if result:
            return result
    except Exception:
        pass

    return None


def find_submit_button(driver):
    """Find the Update/Save submit button using multiple strategies."""
    # Strategy 1: ConfirmBar - the green Update button at the bottom
    try:
        bar = driver.find_element(By.CSS_SELECTOR, "div.ConfirmBar, div[class*='ConfirmBar']")
        btns = bar.find_elements(By.CSS_SELECTOR, "button, input[type='submit'], a")
        for btn in btns:
            text = (btn.text or btn.get_attribute("value") or "").strip().lower()
            if "update" in text:
                return btn
    except Exception:
        pass

    # Strategy 2: Submit buttons with Update/Save text
    for sel in ["button[type='submit']", "input[type='submit']", "button", "a.Button"]:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                text = (btn.text or btn.get_attribute("value") or "").strip().lower()
                if "update" in text:
                    return btn
        except Exception:
            continue

    # Strategy 3: XPath broad search
    try:
        return driver.find_element(By.XPATH,
            "//button[contains(translate(text(),'UPDATE','update'),'update')] | "
            "//input[contains(translate(@value,'UPDATE','update'),'update')] | "
            "//a[contains(translate(text(),'UPDATE','update'),'update')]"
        )
    except Exception:
        pass

    # Strategy 4: Any submit button on the page
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        if btns:
            return btns[-1]
    except Exception:
        pass

    return None


def expand_developer_section(driver):
    """Click the Developer section header to expand it if collapsed."""
    try:
        # Find the Developer heading/toggle
        dev_toggles = driver.find_elements(By.XPATH,
            "//*[contains(@id,'developer')] | "
            "//div[contains(@class,'Heading') and contains(text(),'Developer')]"
        )
        for toggle in dev_toggles:
            try:
                # Check if the section is collapsed by looking for hidden input
                parent = toggle.find_element(By.XPATH, "./ancestor::div[contains(@class,'Container')]")
                inputs = parent.find_elements(By.TAG_NAME, "input")
                visible_inputs = [i for i in inputs if i.is_displayed() and i.get_attribute("type") == "text"]
                if not visible_inputs:
                    # Section is collapsed, click to expand
                    toggle.click()
                    time.sleep(0.5)
                    return True
            except Exception:
                continue

        # Also try clicking on Container#developer directly
        try:
            dev_container = driver.find_element(By.CSS_SELECTOR, "div.Container#developer, div[id='developer']")
            dev_container.click()
            time.sleep(0.5)
        except Exception:
            pass

    except Exception:
        pass
    return False


def update_github_folder(driver, template):
    name = template["name"]
    folder_name = template["folder_name"]
    edit_url = template["edit_url"]

    driver.get(edit_url)

    # Wait for page to load
    time.sleep(2)

    # Scroll to bottom to load all sections
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)

    # Expand the Developer section if it's collapsed
    expand_developer_section(driver)
    time.sleep(0.5)

    # Scroll to bottom again after expanding
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)

    # Find the GitHub input
    github_input = find_github_input(driver)

    if not github_input:
        print(f"    Could not find GitHub folder input on: {edit_url}")
        return False

    # Scroll the input into view
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", github_input)
    time.sleep(0.3)

    # Check current value
    current_value = github_input.get_attribute("value").strip()
    if current_value == folder_name:
        print(f"    Already correct (skipping)")
        return "skipped"
    elif current_value:
        print(f"    Current: {current_value}")
        print(f"    Updating to: {folder_name}")
    else:
        print(f"    Empty, setting to: {folder_name}")

    # Click the input field first to focus it
    github_input.click()
    time.sleep(0.2)

    # Select all existing text and delete it
    from selenium.webdriver.common.keys import Keys
    github_input.send_keys(Keys.COMMAND + "a")
    github_input.send_keys(Keys.DELETE)
    time.sleep(0.2)

    # Type the folder name
    github_input.send_keys(folder_name)
    time.sleep(0.5)

    # Verify
    entered = github_input.get_attribute("value").strip()
    if entered != folder_name:
        print(f"    Input mismatch! Expected: {folder_name}")
        print(f"    Got: {entered}")
        # Last resort: JavaScript
        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true})); "
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            github_input, folder_name
        )
        time.sleep(0.3)
        entered = github_input.get_attribute("value").strip()

    if entered != folder_name:
        print(f"    STILL mismatched after retry. Skipping this template.")
        return False

    # Find and click Update button
    save_btn = find_submit_button(driver)

    if not save_btn:
        print(f"    Could not find Update button")
        return False

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
    time.sleep(0.2)
    save_btn.click()
    time.sleep(2)

    print(f"    Done!")
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

    print(f"\n" + "-" * 60)
    print(f"  Hub : {hub_name} ({base_url})")
    print("-" * 60)

    print(f"\nConnecting to browser...")
    try:
        driver = connect_to_browser()
    except Exception as e:
        print(f"\nCould not connect to browser: {e}")
        print("\nRun template_downloader.py first to open the browser,")
        print("or launch your browser with --remote-debugging-port=9222")
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
        print("\nDone!")