# Improvement Tasks

A checklist of everything worth fixing in this project, written in plain language.

Each task says:

- **What to do**
- **Where** the problem lives
- **Why it matters**
- **How to know it's fixed**

Work through **Section 1** first. Those are actual bugs. Everything after that makes the
project easier to maintain and extend.

---

## Section 1: Fix the bugs (do this first)

### 1.1 Stop saving the same business twice

**Where:** `app/scraper/search.py`, function `_store`

**What happens now:**
The code checks whether a business already exists in the database. If it finds a match,
it labels the result a "duplicate". But it still saves the business as a brand new row
anyway. So the summary says "Duplicates: 6" while the database quietly grows by 6 extra rows.

**Why it matters:**
You end up with the same dentist listed 3 or 4 times in your CSV. That defeats the whole
point of the project.

**What to do:**
If the matching row was found by its `source_id`, update that row.
If it was found by matching name and address, update *that* row instead of inserting a new one.
In other words: update the old row's `id` rather than always calling `upsert`.

**How to verify it's fixed:**
Run this twice with the same business but two different `source_id` values.
It should say `1`, not `2`.

```python
import os, tempfile
from app.database.connection import DatabaseConnection
from app.database.repository import BusinessRepository
from app.scraper.business import Business

d = tempfile.mkdtemp()
repo = BusinessRepository(DatabaseConnection(os.path.join(d, "t.db")))
repo.initialize()

repo.upsert(Business(name="ABC Dental", address="Gulberg, Lahore",
                     source="google_maps", source_id="key-1").to_record())
repo.upsert(Business(name="ABC Dental", address="Gulberg, Lahore",
                     source="google_maps", source_id="key-2").to_record())

print(repo.count())   # want: 1    currently: 2
```

---

### 1.2 Block rows that have no `source_id`

**Where:** `app/database/models.py`, the `UNIQUE(source, source_id)` line

**What happens now:**
SQLite treats empty values (`NULL`) as "all different from each other". So the uniqueness
rule stops working the moment `source_id` is missing. Two identical rows can be saved.

**Why it matters:**
Most rows get a made-up `source_id` as a safety net, so this bug stays hidden. But the
day a page layout changes and that safety net fails, duplicates come flooding back.

**What to do:**
Pick one approach:

- Make `source_id` mandatory (`NOT NULL`) and guarantee it is always filled in before saving, or
- Use an index that ignores `NULL`, so identical empty values still collide.

**How to verify it's fixed:**
Save the same business twice with `source_id=None`. The database should hold **1** row.

---

### 1.3 Stop exporting the wrong data

**Where:** `main.py`, function `export_results`

**What happens now:**
When the current search finds nothing, the code quietly falls back to exporting *every row
in the entire database*.

```python
records = repo.get_by_search(config.keyword, config.location)
if not records:
    records = repo.get_all()      # <-- the trap
```

So a search for `dentists` in `Lahore` that returns nothing will hand you a file called
`dentists_lahore.csv` full of restaurants from Karachi.

**Why it matters:**
Silently wrong output is worse than no output. You could send that file to a client.

**What to do:**
Remove the fallback. If the search found nothing, say so and don't create a file.
If you want an "export everything" option, make it a separate flag like `--export-all`.

---

### 1.4 Make failures visible to the shell

**Where:** `main.py`, function `run_search` and `main`

**What happens now:**
When a job fails, the error is printed and then the program finishes normally. The exit
code is always `0`, which means "success".

**Why it matters:**
If you ever run this on a schedule, or from a script, or in CI, you'll never find out it
crashed. The shell reports success either way.

**What to do:**
Return a success/failure value from `run_search`. In `main`, call `sys.exit(1)` when it failed.

**How to verify it's fixed:**
In PowerShell: `python main.py --keyword x --location y; Write-Output $LASTEXITCODE`
It should print `1` when the job fails.

---

### 1.5 Make name and address matching actually work

**Where:** `app/database/models.py` (`BUSINESS_SELECT_BY_NAME_ADDRESS`) and
`app/scraper/search.py` (`_store`)

**What happens now:**
Two problems:

1. The lookup passes the **original** name and address, but the database only compares them
   after turning them lowercase. It does not remove punctuation or extra spaces.
   So `"ABC Dental Clinic - Lahore"` will never match `"abc dental clinic"`.
   The normalizer that *would* fix this exists but is never called here.
2. If the stored address is empty, the comparison returns "unknown" instead of "no match",
   so businesses without an address can never be matched at all.

**Why it matters:**
Name and address is your last line of defence for deduplication. Right now it barely works.

**What to do:**
Run both values through `Normalizer.normalize_name()` and `Normalizer.normalize_address()`
before querying, and store the normalized versions too so later runs can find them.
Handle the empty-address case explicitly.

---

### 1.6 Use phone number and website for matching

**Where:** `app/scraper/search.py`, function `_store`

**What happens now:**
The project only matches on `source_id` and on name+address. Phone number and website are
collected and saved, but never used to spot a duplicate.

**Why it matters:**
The same business often appears under slightly different names in different searches
("ABC Dental" vs "ABC Dental Clinic"). The phone number never changes. That's the most
reliable clue you have, and you're throwing it away.

**What to do:**
Before inserting, look for an existing row with the same normalized phone, or the same
website domain. If found, update that row.

---

## Section 2: Remove the duplicated code

The project has two copies of several things. They will slowly drift apart, and the
differences will cause confusing bugs.

### 2.1 Delete the unused `Deduplicator` class

**Where:** `app/processing/normalizer.py`, near the bottom

This class is never used by anything. Worse, it is broken: it tries to call
`repository.normalize_phone(...)`, a method that does not exist on the repository, so its
phone and website checks always silently fail. The working version lives in
`app/processing/deduplicator.py`. Delete this one.

### 2.2 Delete the unused `SearchRepository` class

**Where:** `app/database/repository.py`

`BusinessRepository` already has `insert_search` and `update_search` that do the same job.
`SearchRepository` is never imported. Keep one version.

### 2.3 Merge `Business` and `BusinessRecord`

**Where:** `app/scraper/business.py` and `app/database/models.py`

These are two classes with the exact same 18 fields. `Business.to_record()` just copies
every field across to a `BusinessRecord`. Make one class (a Python `dataclass` would cut
this file down a lot) and use it everywhere.

### 2.4 Delete the dead parser helpers

**Where:** `app/scraper/parser.py`, the "Legacy helpers" section

`parse_basic_info` and `parse_from_html` are only used by a single test, and
`parse_from_html` launches a whole browser just to read some HTML. Delete both, and delete
the test that depends on them (`tests/test_parser.py`, class `TestParseFromHtml`).

### 2.5 Delete the unused validator

**Where:** `app/processing/validator.py`

Nothing in the app calls `BusinessValidator`. Either wire it in before saving a business
(which is a genuinely good idea) or remove it.

### 2.6 Delete `check_schema.py`

**Where:** repo root

A three-line debugging script that prints the table schema. Not worth keeping at the top
level. Delete it.

---

## Section 3: Improve the database layer

### 3.1 Stop reopening the database for every single operation

**Where:** `app/database/connection.py` and `app/database/repository.py`

Every method calls `connect()`, which opens a brand new SQLite connection, does its work,
and closes it. During a scrape that happens once per business, including the commit.
Opening a connection with WAL mode enabled is not free.

**What to do:** Make `connect()` return the existing connection if one is already open.
Add a `transaction()` helper so a batch of saves can be committed once at the end.

### 3.2 Stop reading the database by column position

**Where:** `app/database/repository.py`

Rows are converted with `BusinessRecord(*row)`, which fills in fields by position. Every
read also uses `SELECT *`. If you ever add a column anywhere except the very end, every
single read breaks at runtime with a confusing error.

**What to do:** Set `conn.row_factory = sqlite3.Row` and read fields by name.

### 3.3 Type the `upsert` parameter properly

**Where:** `app/database/repository.py`, function `upsert`

It takes `record: object` and then makes 18 defensive `getattr(record, x, default)`
lookups to read values out of a class the file controls. Declare it as `BusinessRecord`
and access the fields directly.

### 3.4 Add indexes for the columns you search on

**Where:** `app/database/models.py`

`search_keyword`, `search_location`, `phone`, and `website` have no index. Every lookup
on them scans the whole table. This will hurt once the enrichment stage starts querying
by phone and website. Add indexes when you create the table.

### 3.5 Close log files before clearing handlers

**Where:** `app/logging.py`

`logger.handlers = []` drops the handlers without closing their file handles. If
`setup_logging()` is ever called twice, a file handle leaks. Close each handler first.

### 3.6 Don't create the log file just by importing the app

**Where:** `app/logging.py`, last line

Right now, `logger = setup_logging(...)` runs at import time. That means even
`python main.py --help` creates `data/logs/engine.log` on disk. Set up logging when a job
actually starts instead.

---

## Section 4: Add tests

The current tests are good — 47 of them pass, and the parser tests correctly avoid
needing a live browser. But they miss the code where the bugs actually live.

### 4.1 Write tests for the repository

**Create:** `tests/test_repository.py`

Use pytest's `tmp_path` fixture with a real SQLite file. At minimum, cover:

- Saving a business twice results in **1** row
- Saving with `source_id=None` twice results in **1** row
- `get_by_search` returns only that search's rows
- `first_seen_at` stays at its original value when a row is updated

Tasks 1.1 and 1.2 would have been caught by these tests.

### 4.2 Write tests for `SearchEngine`

**Create:** `tests/test_search_engine.py`

This is 412 lines of scroll, retry and state-machine logic with **zero** tests — it is the
riskiest file in the project. Pass in a fake `page` object (the pattern already exists in
`tests/test_parser.py` as `FakeNode`) and test the counting, the duplicate skipping, and
the retry behaviour.

### 4.3 Add a regression test for the double-save bug

One test that specifically locks in the fix from task 1.1, so it can never come back.

---

## Section 5: Repository hygiene

### 5.1 Add a `pyproject.toml`

There is currently no single file describing the project. A `pyproject.toml` gives you one
place for the project name, Python version requirement, dependencies, and configuration for
pytest, the linter and the type checker.

### 5.2 Pin the dependencies

`requirements.txt` says `playwright>=1.40.0`, which allows any newer version. Pin the exact
versions you have tested, or use a lock file. Also record which Python versions you support
(the README says 3.11+, but this machine is running 3.14).

### 5.3 Separate test dependencies from runtime dependencies

`pytest` is currently in `requirements.txt`, so installing the app to use it also installs
the test runner. Move it to a `requirements-dev.txt` or a `[dev]` extra in `pyproject.toml`.

### 5.4 Add a linter

Add **ruff** (fast, replaces flake8 + isort + more) and run it on `app/` and `tests/`.
You will likely want to fix the tuple return annotations in `parser.py` first —
`-> (Optional[float], Optional[int])` is not a real type annotation, it is just a tuple
expression, so type checkers ignore it. Use `tuple[Optional[float], Optional[int]]`.

### 5.5 Add continuous integration

A small GitHub Actions workflow that runs `pytest` and the linter on every push. This
takes about 20 lines and would have caught several of the bugs in Section 1.

### 5.6 Add a license

The README says to pick one but no file exists. **MIT** is a safe default for this kind of
tool. If you plan to keep it private forever it matters less, but decide deliberately.

### 5.7 Fix the `.gitignore` typo

Line 17 says `.pyproject.toml`. That is almost certainly meant to be nothing at all — and
it would hide the file from task 5.1. Delete that line.

### 5.8 Rename `app/logging.py`

It shares a name with Python's built-in `logging` module. It works today, but it is a
recurring source of confusion when someone writes `import logging` inside the app.
Rename it to `app/log.py` or `app/logger.py`.

---

## Section 6: Configuration

### 6.1 Make the country and language configurable

Two places quietly hardcode Pakistan:

- `app/scraper/search.py` — the search URL ends with `?gl=country-pk&hl=en`
- `app/processing/normalizer.py` — `normalize_phone` only understands `+92` numbers

The README advertises configurable locations, but the config file has no `country` or
`language` setting at all. Add them to `DEFAULT_SETTINGS`, read them from `.env`, and add
`--country` and `--language` command line flags.

### 6.2 Handle phone numbers from other countries

Once the country is configurable, `normalize_phone` should use it. Numbers from countries
you don't recognize should be saved in a clean but unconverted form rather than returned
raw.

---

## Section 7: Command line interface

### 7.1 Add subcommands

Right now the tool can only do one thing: run a search. Turn it into proper subcommands so
the other capabilities of the database become reachable:

```
python main.py search --keyword "dentists" --location "Lahore" --limit 100
python main.py history
python main.py export --keyword "dentists" --location "Lahore"
```

`BusinessRepository` already supports search history, but there is no way to view it.

### 7.2 Add a `--resume` flag

The README lists "Resumable scraping jobs" as a current feature, but nothing in the code
resumes anything. The `search_history` table records `status` but never reads it back.
Either implement resuming (find the last unfinished job and continue from its saved
position) or remove the claim from the README.

### 7.3 Add a progress bar

The README's example output shows `[████████████░░] 82%`. The real output is one log line
per business. Either add a progress bar (`tqdm` works well) or correct the README.

---

## Section 8: Make the README honest

### 8.1 Correct the feature list

The "Current / Core Features" section lists things the code does not do:

- **"Resumable scraping jobs"** — not implemented (see task 7.2)
- **"Structured logging"** — the log format is plain text, not structured. Either implement
  JSON logging or reword it.

### 8.2 Tick the roadmap boxes that are done

Phase 1 is essentially complete, and most of Phase 2 as well. Update the checkboxes so the
roadmap reflects reality.

### 8.3 Shorten the README and move the rest to `docs/`

The README is 1,147 lines and most of it is future plans and philosophy. Suggestion: keep
the README to roughly 150 lines covering what the project is, how to install it, how to run
it, and the current status. Move the architecture diagrams, roadmap, enrichment plans and
design principles into a `docs/` folder. Right now a new contributor cannot tell what
actually works.

---

## Suggested order

| Step | Tasks | Why here |
|------|-------|----------|
| 1 | 1.1 – 1.6 | Real bugs producing wrong data |
| 2 | 4.1, 4.3 | Lock those fixes in with tests |
| 3 | 2.1 – 2.6 | Remove code that causes confusion |
| 4 | 5.1, 5.2, 5.4, 5.5 | Tooling that catches mistakes early |
| 5 | 3.1 – 3.6 | Performance and robustness |
| 6 | 6.1, 6.2 | Needed before any non-Pakistani searches |
| 7 | 7.1 – 7.3, 4.2 | Usability |
| 8 | 5.3, 5.6, 5.7, 5.8, 8.1 – 8.3 | Polish |

---

*Created from a full code review. All 47 existing tests currently pass, and none of them
cover the bugs listed in Section 1. A desktop GUI and PyInstaller packaging have
since been added (see Phase 6).*
