# Dokio Scripts

> Because Jake is too lazy to click through 500+ templates across 30+ hubs manually.

Two Python scripts for managing Dokio templates.

---

## Scripts

### 1. `template_downloader.py` — Download all templates

Downloads, unzips, and names all templates from any Dokio hub.

- Type a hub name like `ipa` or `poolwerx`
- Scans ALL pages automatically
- Skips Static PDF and Archive templates
- Unzips into named folders: `Q33D3U - Hyperlocal Email 2025`
- Files inside keep their original names
- Saves to `~/Documents/<hub-name>-templates/`

### 2. `github_folder_updater.py` — Set GitHub repo folder names

Fills in the "GitHub repo folder" field in each template's Edit Settings.

- Uses the same `DokioID - Template Name` format as the downloader
- Goes to each template's Edit Settings page automatically
- Fills in the GitHub folder input and clicks Update
- Skips templates that already have a value set
- Skips Static PDF and Archive templates

---

## Requirements

- Mac
- Python 3.9+ (check with `python3 --version`)
- One of: **Google Chrome**, **Chrome Canary**, **Brave**, or **Firefox**
- Okta access to the Dokio admin panel

---

## Setup (One-time)

```bash
pip3 install selenium requests
```

> Use `pip3`, not `pip` on Mac.

---

## How to use

### Step 1 — Download templates

```bash
python3 template_downloader.py
```

```
Which Dokio hub?
  Hub: ipa

Which browser?
  [1] Google Chrome
  Enter number: 1

  Launching Google Chrome...
  Log in via Okta, then come back here.
  Press Enter when ready...

  Scanning page 1...
  Scanning page 2...
  Total: 142 templates

[1/142] Q33D3U - Hyperlocal Email 2025 - with mask 190326
    index.html
    data.yaml
    -> 2 file(s) in Q33D3U - Hyperlocal Email 2025 - with mask 190326/
...

Downloaded: 142
Files saved to: ~/Documents/ipa-templates/
```

### Step 2 — Set GitHub folder names

```bash
python3 github_folder_updater.py
```

```
Which Dokio hub?
  Hub: ipa

Which browser?
  [1] Google Chrome
  Enter number: 1

  Launching Google Chrome...
  Press Enter when ready...

  Scanning page 1...
  Total: 142 templates

Ready to update 142 templates. Continue? (y/n): y

[1/142] Q33D3U - Hyperlocal Email 2025 - with mask 190326
    Set to: Q33D3U - Hyperlocal Email 2025 - with mask 190326

[2/142] A7B2C1 - Newsletter Header Banner
    Already set: A7B2C1 - Newsletter Header Banner (skipping)
...

Updated: 130
Skipped: 12 (already had a value)
Failed:  0
```

---

## Output

Templates are saved to your Documents folder:

```
~/Documents/ipa-templates/
├── Q33D3U - Hyperlocal Email 2025 - with mask 190326/
│   ├── index.html
│   ├── data.yaml
│   └── preview.png
├── A7B2C1 - Newsletter Header Banner/
│   ├── banner-300x250.png
│   └── banner-728x90.png
└── ...
```

**Folder name** = `DokioID - Template Name` (same name used in GitHub settings)
**Files inside** = original filenames, untouched

---

## Troubleshooting

**`Could not connect to browser`**
Close the browser and try again. The script auto-launches it for you.

**`No templates found`**
Make sure you're logged in via Okta and the hub name is correct.

**`FAILED: Session expired`**
Refresh the browser, log in again, re-run the script.

**`Could not find GitHub folder input`**
The template type may not support GitHub folders. These will show as failed.

**`zsh: command not found: pip`**
Use `pip3`: `pip3 install selenium requests`

---

*Made by Jake Villar · Internal use only*