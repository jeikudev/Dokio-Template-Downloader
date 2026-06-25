# Multi-Select Template Types — Design

**Date:** 2026-06-26
**File touched:** `template_downloader.py` (single file)

## Problem

`template_downloader.py` downloads every template in a hub except those whose
Details column contains `static` or `archive` (hardcoded skip at the row loop in
`collect_all_templates`). The user wants to choose which template **types** to
download, selecting multiple types per run.

## Type taxonomy

Six selectable types, classified from the **Details** column's leading token:

| # | Type       | Details column example                  |
|---|------------|------------------------------------------|
| 1 | PDF        | `PDF - A4 (210×297mm)`                    |
| 2 | Static PDF | `Static PDF - A4 (210×297mm)`            |
| 3 | Email      | `Email - ...`                            |
| 4 | Archive    | `Archive`                                |
| 5 | Video      | `Video - 1080×1080px / 00:00:15`         |
| 6 | General    | `General - ...`                          |

`PDF` and `Static PDF` are split deliberately: the old script kept `PDF` and
skipped `Static PDF`. Splitting preserves that control while allowing Static PDF
to be included when wanted.

## Filtering method

**Scan-all, filter locally.** Keep the existing full-page scan (57 pages / ~1130
templates). For each row, classify its type from the Details text and keep the
row only if its type is in the user's selected set. No dependency on the site's
URL filter params.

## Components

### `classify_type(details_text) -> str | None`

Normalizes a row's joined-column text to one of the six type labels, or `None`
if unrecognized.

- Input is lowercased.
- **Precedence:** check `static pdf` **before** `pdf` (Static PDF rows contain
  both "static" and "pdf").
- Order of checks: `static pdf` → `pdf` → `email` → `archive` → `video` →
  `general` → else `None`.
- Token matching is safe: the `div[class*='_column']` elements hold only Dokio
  ID (alphanumeric code), Details, and the modified date — never the template
  name. So a template titled "GWM Video Guide" cannot produce a false "video"
  match, because the name lives in `a._title`, not in the column divs.

### `choose_types() -> set[str]`

Interactive prompt, run after browser selection and before scanning. Output:

```
Which template types? (comma-separated, or 'all')
  [1] PDF
  [2] Static PDF
  [3] Email
  [4] Archive
  [5] Video
  [6] General

  Enter = default (PDF, Email, Video, General — skips Static PDF & Archive)
  Types:
```

Parsing rules:

- `all` (any case) → all six types.
- Empty input (Enter) → default set `{PDF, Email, Video, General}` (mirrors the
  old skip-Static-PDF-and-Archive behavior).
- Comma-separated numbers (e.g. `1,3,5`) → those types. Whitespace tolerated.
- Any token out of range, non-numeric, or producing an empty set → print an
  error and re-prompt.
- Returns a set of canonical type-label strings (matching `classify_type`
  output).

### `collect_all_templates(driver, templates_url, selected_types)`

Signature gains `selected_types`. The hardcoded skip line is replaced:

- Old: `if "static" in details_text or "archive" in details_text: skip`
- New: `row_type = classify_type(details_text); if row_type not in selected_types: skip`

Per-page tally label changes from `skipped (Static/Archive)` to
`skipped (type not selected)`.

### `__main__` wiring

- Call `selected_types = choose_types()` after `choose_browser()`.
- Pass `selected_types` into `collect_all_templates(...)`.
- Echo the chosen types in the run-summary block (the `---` framed block before
  `launch_browser`).
- Update the WELCOME banner line that reads "Skips Static PDF and Archive
  templates" to reflect that types are now user-selected.

## Out of scope

Download, unzip, file-handling, session, and pagination logic are unchanged.
`github_folder_updater.py` is not touched.

## Testing

Manual, against a live hub (script requires a logged-in browser; no automated
harness exists in this repo):

1. Run, press Enter at the type prompt → confirm Static PDF and Archive rows are
   skipped, others downloaded (matches old behavior).
2. Run, enter `2` (Static PDF only) → confirm only Static PDF rows collected.
3. Run, enter `all` → confirm every row collected, nothing skipped.
4. Run, enter invalid (`9`, `abc`, empty-after-trim) → confirm re-prompt.
5. Spot-check `classify_type` precedence: a `Static PDF` row classifies as
   `Static PDF`, not `PDF`.
