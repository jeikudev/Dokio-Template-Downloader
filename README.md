# Dokio Template Downloader Script

> Because Jake is too lazy to click through 300+ templates across 50+ hubs manually.

A Python script that automatically downloads all templates from any Dokio hub.

**What it does:**
- Type a hub name like `bupa-sam` or `poolwerx` — no full URLs needed
- Pick your browser — it auto-launches with remote debugging in a new terminal
- Scans ALL pages of templates automatically
- Skips Static PDF and Archive templates
- Downloads and unzips into properly named folders
- **Folder** gets renamed (e.g. `746K64 - Template Name`), files inside keep their original names
- Auto-saves to `~/Documents/<hub-name>-templates/`

---

## Requirements

- Mac
- Python 3.9+ (already on Mac — check with `python3 --version`)
- One of: **Google Chrome**, **Chrome Canary**, **Brave**, or **Firefox**
- Okta access to the Dokio admin panel

---

## Setup (One-time)

### Install dependencies

```bash
pip3 install selenium requests
```

> Use `pip3`, not `pip` on Mac.

---

## How to use

### 1. Run the script

```bash
cd ~/Projects/Scripts
python3 template_downloader.py
```

### 2. Answer two questions

```
Which Dokio hub?
  Type the hub name or full URL.
  Examples: bupa-sam, poolwerx, ipa, australian-unity

  Hub: bupa-sam
  Hub URL    : https://bupa-sam.dokio.co
  Save to    : ~/Documents/bupa-sam-templates

Which browser?
  [1] Google Chrome  (installed)
  [2] Chrome Canary  (installed)
  [3] Brave          (installed)
  [4] Firefox        (installed)

  Enter number: 1
```

### 3. Browser launches automatically

A **new Terminal window** opens and launches your browser with remote debugging. Log in via Okta in that browser, then come back to the original terminal and press Enter.

> You only need to log in once — the session is saved.

### 4. It runs automatically

The script scans all pages, downloads, unzips, and names everything.

---

## Where are my files?

Auto-saved to Documents, named after the hub:

```
~/Documents/bupa-sam-templates/
├── VJ64UA - OVC 8WF Feb Agents Incentive Guide/
│   ├── index.html
│   ├── data.yaml
│   └── preview.png
├── A63F34 - OVC 8WF Feb 26 email banners/
│   ├── banner-300x250.png
│   ├── banner-728x90.png
│   └── banner-160x600.png
└── ...
```

**Folder** = `DokioID - Template Name`
**Files inside** = original filenames, untouched

---

## Troubleshooting

**`Could not connect to browser`**
The browser didn't launch properly. Close it and try again, or launch manually with `--remote-debugging-port=9222`.

**`No templates found`**
Make sure you're logged in via Okta and the hub name is correct.

**`FAILED: Session expired`**
Go back to the browser, refresh, log in again, then re-run the script.

**`zsh: command not found: pip`**
Use `pip3` on Mac: `pip3 install selenium requests`

---

*Made by Jake Villar · Internal use only*