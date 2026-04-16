# Dokio Scripts

> Because Jake is too lazy to click through 300+ templates across 50+ hubs manually.

Two Python scripts for managing Dokio templates. Run them in order — the first opens the browser, the second reuses it.

---

## What's in here?

### `template_downloader.py` — Download all templates

- Type a hub name like `ipa` or `poolwerx` — no full URLs needed
- Picks your browser and launches it with remote debugging
- Scans ALL pages automatically (however many there are)
- Skips Static PDF and Archive templates
- Downloads, unzips, and organizes into named folders
- Folder: `Q33D3U - Hyperlocal Email 2025` / files inside: original names untouched
- Saves to `~/Documents/<hub-name>-templates/`

### `github_folder_updater.py` — Set GitHub repo folder names

- Connects to the **same browser** the downloader opened (no new browser)
- Goes to each template's Edit Settings page
- Fills in the "GitHub repo folder" field with `DokioID - Template Name`
- Clicks Update to save
- Skips templates that already have a value set
- Skips Static PDF and Archive templates

---

## Requirements

- **Mac**
- **Python 3.9+** — already on Mac, check with `python3 --version`
- **Git** — already on Mac
- **One of these browsers:** Google Chrome, Chrome Canary, or Brave
- **Okta access** to the Dokio admin panel

---

## Getting started

### 1. Clone the repo

Open **Terminal** and run:

```bash
git clone git@github.com:jeikudev/Dokio-Template-Downloader.git
```

### 2. Go into the folder

```bash
cd Dokio-Template-Downloader
```

### 3. Install Python dependencies

```bash
pip3 install selenium requests
```

> If you get `zsh: command not found: pip`, use `pip3` — that's normal on Mac.

You're all set. From now on you just `cd` into this folder and run the scripts.

---

## How to use

### Step 1 — Download templates

Make sure you're in the repo folder, then run:

```bash
cd ~/Dokio-Template-Downloader
python3 template_downloader.py
```

The script will walk you through everything:

```
+==============================================================+
|          Dokio Template Downloader Script  v3.0               |
+==============================================================+

Which Dokio hub?
  Examples: bupa-sam, poolwerx, ipa, australian-unity

  Hub: ipa
  Hub URL    : https://ipa.dokio.co
  Save to    : ~/Documents/ipa-templates

Which browser?
  [1] Google Chrome  (installed)
  [2] Chrome Canary  (installed)
  [3] Brave          (installed)

  Enter number: 1

  Launching Google Chrome...
  Google Chrome should now be open!

  In the browser window:
    1. Log in via Okta if needed
    2. Come back to THIS terminal

  Press Enter when you're logged in and ready...
```

Once you press Enter it runs automatically:

```
Scanning templates...
  Scanning page 1...
    18 added, 2 skipped (Static/Archive)
  Scanning page 2...
    20 added, 0 skipped (Static/Archive)
  ...
  Total: 142 templates across 8 page(s).

[1/142] Q33D3U - Hyperlocal Email 2025 - with mask 190326
    index.html
    data.yaml
    preview.png
    -> 3 file(s) in Q33D3U - Hyperlocal Email 2025 - with mask 190326/

[2/142] A7B2C1 - Newsletter Header Banner
    banner-300x250.png
    banner-728x90.png
    -> 2 file(s) in A7B2C1 - Newsletter Header Banner/
...

==============================================================
  Downloaded : 142
  Failed     : 0

  Files saved to: ~/Documents/ipa-templates
==============================================================

Browser window left open. Done!
You can now run: python3 github_folder_updater.py
```

---

### Step 2 — Set GitHub folder names

**Don't close the browser!** The updater script connects to the same one.

```bash
python3 github_folder_updater.py
```

```
+==============================================================+
|       Dokio GitHub Folder Name Updater Script  v1.0           |
+==============================================================+

Which Dokio hub?
  Hub: ipa
  Hub URL : https://ipa.dokio.co

Connecting to browser...
  Connected to browser! (page: Templates)

Scanning templates...
  Total: 142 templates across 8 page(s).

Ready to update 142 templates. Continue? (y/n): y

[1/142] Q33D3U - Hyperlocal Email 2025 - with mask 190326
    Set to: Q33D3U - Hyperlocal Email 2025 - with mask 190326

[2/142] A7B2C1 - Newsletter Header Banner
    Already set: A7B2C1 - Newsletter Header Banner (skipping)

[3/142] B9D4E2 - Monthly Promo Flyer
    Set to: B9D4E2 - Monthly Promo Flyer
...

==============================================================
  Updated  : 130
  Skipped  : 12 (already had a value)
  Failed   : 0
==============================================================

Done!
```

---

## Where are my files?

Saved to your **Documents** folder, named after the hub:

```
~/Documents/ipa-templates/
├── Q33D3U - Hyperlocal Email 2025 - with mask 190326/
│   ├── index.html
│   ├── data.yaml
│   └── preview.png
├── A7B2C1 - Newsletter Header Banner/
│   ├── banner-300x250.png
│   └── banner-728x90.png
├── B9D4E2 - Monthly Promo Flyer/
│   └── flyer.pdf
└── ...
```

| What | Naming |
|------|--------|
| **Folder** | `DokioID - Template Name` |
| **Files inside** | Original filenames, untouched |
| **GitHub folder field** | Same as the folder name |

---

## Quick reference

| Task | Command |
|------|---------|
| Clone the repo | `git clone git@github.com:jeikudev/Dokio-Template-Downloader.git` |
| Go into the folder | `cd Dokio-Template-Downloader` |
| Install dependencies | `pip3 install selenium requests` |
| Download templates | `python3 template_downloader.py` |
| Set GitHub folder names | `python3 github_folder_updater.py` |

---

## Troubleshooting

### Browser issues

**"Could not connect to browser"**
The browser isn't running with remote debugging. The downloader script launches it for you — run that first. If you closed the browser, just run the downloader again and it'll reopen it.

**"Debug browser already running — reusing it!"**
This is normal! It means the browser from a previous run is still open. The script will just use it.

**Browser launched but nothing happened**
Sometimes the browser needs a moment. Wait a few seconds, log in via Okta, then press Enter.

### Template issues

**"No templates found"**
Make sure the hub name is correct and you're logged in via Okta in the browser.

**"FAILED: Session expired"**
Your Okta session timed out. Go to the browser, refresh, log in again, then re-run the script.

**"Could not find GitHub folder input"**
Some template types may not have the GitHub folder field. These will show as failed — that's expected.

### Setup issues

**"zsh: command not found: pip"**
Use `pip3` on Mac: `pip3 install selenium requests`

**"ModuleNotFoundError: No module named 'selenium'"**
Run the install again: `pip3 install selenium requests`

**"Permission denied" when cloning**
Your SSH key isn't set up for GitHub. Ask Jake or IT to help you add one, or clone with HTTPS instead:
`git clone https://github.com/jeikudev/Dokio-Template-Downloader.git`

---

## Tips

- **Same hub, both scripts?** Run downloader first, then updater. Don't close the browser between them.
- **Different hub?** Just run the scripts again with the new hub name. The browser stays open.
- **Already downloaded before?** The downloader won't overwrite existing folders — it adds `_1`, `_2` suffixes if there's a conflict.
- **Want to stop mid-way?** Press `Ctrl+C` at any time. The browser stays open and you can re-run.
- **Re-running the updater?** It skips templates that already have a GitHub folder set, so it's safe to run multiple times.
- **Pulling updates?** `cd Dokio-Template-Downloader && git pull`

---


*Made by Jake for Natt & Leo ❤︎⁠ · Internal use only*