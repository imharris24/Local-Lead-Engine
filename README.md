# Local Lead Engine

A local-first lead generation and business data collection tool built with **Python, Playwright, and SQLite**.

The goal is simple:

> Turn business search queries into a clean, deduplicated CSV of qualified leads — without depending on Apify or a paid scraping infrastructure.

The project is designed for developers who want full control over the scraping workflow, data storage, enrichment, filtering, and export pipeline.

---

## ⚠️ Legal & Responsible Use

This project is intended for legitimate research, prospecting, and data-processing workflows.

Automated extraction of data from websites may be restricted by their terms of service, robots policies, contracts, or applicable laws. In particular, Google Maps/Google Maps Platform terms place restrictions on scraping, exporting, and using Maps content.

Before using this project against any service, review the applicable terms and make sure your intended use is permitted.

Do not use this project to:

* Circumvent authentication or access controls
* Bypass CAPTCHAs or security mechanisms
* Evade bans or technical restrictions
* Collect sensitive personal information
* Conduct spam or abusive automated outreach

The project should prioritize conservative request rates, transparency, and responsible data handling.

---

# Features

## Current / Core Features

* Local browser automation using Playwright
* Business search workflow
* Business detail extraction
* CSV export
* SQLite persistence
* Duplicate detection
* Retry handling
* Structured logging
* Configurable search queries
* Configurable locations
* Configurable result limits
* Resumable scraping jobs
* No cloud infrastructure required

## Planned Features

* Multiple keyword searches
* Multiple locations
* Search-area subdivision
* Advanced deduplication
* Website discovery
* Website crawling
* Email extraction
* Social profile discovery
* Website technology detection
* Website quality analysis
* Lead scoring
* Custom lead filters
* Export profiles
* Job history
* Desktop UI
* Scheduling
* Multiple output formats

---

# Architecture

The application follows a pipeline architecture:

```text
                 ┌──────────────────┐
                 │   Search Config  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Browser Engine   │
                 │    Playwright    │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Search / Collect │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Business Parser  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Data Normalizer  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │    SQLite DB     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   CSV Exporter   │
                 └──────────────────┘
```

The scraper should not write directly to CSV during extraction.

SQLite acts as the source of truth.

CSV is an output format.

This makes it possible to resume jobs, deduplicate records, update existing businesses, and run additional enrichment without repeatedly scraping the same records.

---

# Technology Stack

| Component          | Technology            |
| ------------------ | --------------------- |
| Language           | Python 3.11+          |
| Browser automation | Playwright            |
| Database           | SQLite                |
| Data processing    | Python                |
| CSV                | Python `csv` / Pandas |
| Configuration      | `.env` / YAML / JSON  |
| Testing            | Pytest                |
| Optional UI        | FastAPI + React       |
| Packaging          | PyInstaller           |

The initial version should remain intentionally small.

Do not introduce a web server or frontend until the scraping engine is stable.

---

# Project Structure

```text
local-lead-engine/
│
├── app/
│   ├── __init__.py
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── browser.py
│   │   ├── search.py
│   │   ├── business.py
│   │   └── parser.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repository.py
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── normalizer.py
│   │   ├── deduplicator.py
│   │   └── validator.py
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   └── csv_exporter.py
│   │
│   ├── config.py
│   └── logging.py
│
├── data/
│   ├── database/
│   │   └── leads.db
│   │
│   ├── exports/
│   │   └── .gitkeep
│   │
│   └── logs/
│       └── .gitkeep
│
├── tests/
│   ├── test_parser.py
│   ├── test_normalizer.py
│   ├── test_deduplicator.py
│   └── test_exporter.py
│
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# Requirements

* Python 3.11 or newer
* Windows, macOS, or Linux
* Chromium/Chrome-compatible browser
* Internet connection for the source website

The application itself does not require:

* Apify
* AWS
* Docker
* Redis
* PostgreSQL
* A VPS
* A paid API

The initial target is a completely local installation.

---

# Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd local-lead-engine
```

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Install Playwright browsers

```bash
playwright install chromium
```

---

## 5. Configure the application

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows:

```powershell
copy .env.example .env
```

Example:

```env
HEADLESS=false
DATABASE_PATH=data/database/leads.db
EXPORT_PATH=data/exports
LOG_LEVEL=INFO
```

No API key should be required for the core local workflow.

---

# Basic Usage

The simplest workflow should look like:

```bash
python main.py \
  --keyword "dentists" \
  --location "Lahore" \
  --limit 100
```

Windows PowerShell:

```powershell
python main.py --keyword "dentists" --location "Lahore" --limit 100
```

Example output:

```text
Local Lead Engine
────────────────────────────────────────

Keyword:    dentists
Location:   Lahore
Limit:      100

Starting browser...

Searching...
Collecting businesses...

[████████████████████░░░░░░] 82%

Discovered: 126
Processed:  100
New:         94
Duplicates:   6
Errors:       0

Export complete.

File:
data/exports/dentists_lahore.csv
```

---

# Search Configuration

A search consists of:

```text
Keyword
Location
Result Limit
```

Example:

```text
Keyword:   "web development agencies"
Location:  "Islamabad"
Limit:     200
```

Multiple searches should eventually be supported:

```yaml
searches:
  - keyword: "dentists"
    location: "Lahore"
    limit: 200

  - keyword: "law firms"
    location: "Islamabad"
    limit: 200

  - keyword: "restaurants"
    location: "Karachi"
    limit: 500
```

Each search should be treated as an independent job.

---

# Data Model

The core business record should contain:

```text
Business
├── id
├── source
├── source_id
├── name
├── category
├── address
├── phone
├── website
├── rating
├── review_count
├── latitude
├── longitude
├── maps_url
├── opening_hours
├── search_keyword
├── search_location
├── first_seen_at
├── last_seen_at
└── scraped_at
```

Additional fields can be added as the project evolves.

---

# Database

SQLite is used as the primary storage layer.

Example:

```text
data/database/leads.db
```

The database provides several advantages over writing directly to CSV.

### Deduplication

A business found by multiple searches should not become multiple records.

### Resumability

If a 500-business job stops at business 327, the application should be able to continue rather than starting from zero.

### Historical data

The application can track when a business was first and last observed.

### Enrichment

Website analysis and lead scoring can happen after the initial collection.

---

# Deduplication

Deduplication should not rely solely on business names.

Possible identifiers, in descending order of reliability:

```text
Source / Place ID
        ↓
Canonical Maps URL
        ↓
Phone number
        ↓
Website domain
        ↓
Normalized name + address
```

A normalized business name might transform:

```text
"ABC Dental Clinic - Lahore"
```

into:

```text
abc dental clinic
```

while phone normalization might transform:

```text
+92 300-1234567
0300 1234567
```

into a consistent representation.

The exact normalization strategy should be configurable.

---

# CSV Output

Example:

```csv
name,category,address,phone,website,rating,review_count,maps_url
ABC Dental Clinic,Dentist,"Gulberg, Lahore",+923001234567,https://example.com,4.7,183,https://...
XYZ Dental,Dentist,"DHA Lahore",+92421234567,,4.2,87,https://...
```

CSV files are stored in:

```text
data/exports/
```

Example:

```text
data/exports/
├── dentists_lahore.csv
├── restaurants_karachi.csv
└── agencies_islamabad.csv
```

---

# Logging

Every job should generate useful logs.

Example:

```text
2026-10-07 18:30:21 INFO  Starting job
2026-10-07 18:30:24 INFO  Browser started
2026-10-07 18:30:29 INFO  Search loaded
2026-10-07 18:30:31 INFO  Discovered 47 results
2026-10-07 18:30:34 INFO  Processing business 1/47
2026-10-07 18:30:35 INFO  Processing business 2/47
2026-10-07 18:31:12 WARN  Business 19 failed
2026-10-07 18:31:14 INFO  Retrying business 19
2026-10-07 18:32:05 INFO  Job complete
```

Logs should be written to:

```text
data/logs/
```

---

# Error Handling

The scraper should assume that failures will happen.

Possible failures include:

* Page navigation errors
* Timeouts
* Missing fields
* Unexpected page structure
* Browser crashes
* Temporary network failures
* Incomplete business data
* Search results changing
* Source-site UI changes

A single failed business should **not terminate the entire job**.

Instead:

```text
Business 1 → Success
Business 2 → Success
Business 3 → Failed → Retry
Business 4 → Success
Business 5 → Success
```

At the end:

```text
Processed:  100
Successful: 97
Failed:      3
```

Failed records should be logged for later inspection.

---

# Retry Strategy

Retries should be conservative.

Example:

```text
Attempt 1
   ↓
Wait
   ↓
Attempt 2
   ↓
Wait longer
   ↓
Attempt 3
   ↓
Mark failed
```

Avoid aggressive request loops.

The objective is reliability, not maximum request speed.

---

# Search Coverage

A common mistake is assuming:

```text
One search = All businesses
```

It isn't.

Search results can vary based on:

* Query
* Location
* Map viewport
* Search ranking
* Result availability
* Geographic density
* Search wording

For broader coverage, the application should eventually support multiple related searches.

For example:

```text
dentist Lahore
dental clinic Lahore
dentist Gulberg Lahore
dentist DHA Lahore
dental hospital Lahore
```

The database then handles deduplication.

---

# Lead Enrichment

The long-term purpose of this project is not merely collecting business listings.

The system should eventually support enrichment.

Example:

```text
Google Maps
     ↓
Business
     ↓
Website
     ↓
Website Analysis
     ↓
Lead Score
```

Potential enrichment fields:

```text
website_exists
website_domain
ssl_enabled
website_status
website_load_time
mobile_friendly
contact_email
contact_page
facebook_url
instagram_url
linkedin_url
cms
analytics
technology_stack
```

Enrichment should be implemented as a separate pipeline.

This prevents the Maps collector from becoming unnecessarily complicated.

---

# Lead Scoring

Eventually businesses can be scored according to sales relevance.

Example:

```text
Lead Score
───────────

No website                  +30
Poor website                +20
No HTTPS                    +15
Low mobile quality          +10
No contact form             +10
No social presence           +5
High review count            +5
```

Example result:

```text
ABC Dental Clinic

Lead Score: 90

Reasons:
✓ No website
✓ 183 Google reviews
✓ Established business
✓ Strong local presence

Opportunity: HIGH
```

The scoring model should be configurable rather than hard-coded.

---

# Design Principles

## 1. Local First

The application should work without a cloud backend.

```text
Laptop
 ├── Browser
 ├── Python
 ├── SQLite
 └── CSV
```

No server should be necessary for the core functionality.

---

## 2. Database First, CSV Second

CSV is an export format.

SQLite is the application's source of truth.

---

## 3. Modular Scraping

Do not put the entire scraper inside `main.py`.

Keep these concerns separate:

```text
Browser
Search
Extraction
Parsing
Normalization
Storage
Export
Enrichment
Scoring
```

This makes maintenance much easier when the source website changes.

---

## 4. Fail Gracefully

One bad business should never destroy an entire job.

---

## 5. Resumable Jobs

Long-running jobs must be restartable.

A crash should not mean:

> "Start the whole thing again."

---

## 6. Conservative Automation

Do not optimize for maximum scraping speed.

Optimize for:

```text
Reliability
+
Data quality
+
Reproducibility
```

---

# Development Roadmap

## Phase 1 — Core Scraper

* [ ] Playwright setup
* [ ] Browser management
* [ ] Search input
* [ ] Search result collection
* [ ] Business extraction
* [ ] Basic CSV export

---

## Phase 2 — Persistence

* [ ] SQLite
* [ ] Business model
* [ ] Deduplication
* [ ] Job tracking
* [ ] Resume support
* [ ] Error logging

---

## Phase 3 — Search Coverage

* [ ] Multiple queries
* [ ] Multiple locations
* [ ] Search subdivisions
* [ ] Configurable limits
* [ ] Search history

---

## Phase 4 — Enrichment

* [ ] Website discovery
* [ ] Website crawler
* [ ] Email discovery
* [ ] Social links
* [ ] Technology detection
* [ ] Website quality checks

---

## Phase 5 — Lead Intelligence

* [ ] Lead scoring
* [ ] Custom scoring rules
* [ ] Lead filters
* [ ] Sales categories
* [ ] Opportunity detection

---

## Phase 6 — User Interface

Possible architecture:

```text
React
  ↓
FastAPI
  ↓
Python Lead Engine
  ↓
SQLite
```

Potential UI:

```text
┌─────────────────────────────────────────────┐
│ Local Lead Engine                           │
├─────────────────────────────────────────────┤
│                                             │
│ Keyword                                     │
│ [ dentists                              ]   │
│                                             │
│ Location                                    │
│ [ Lahore                                ]   │
│                                             │
│ Limit                                       │
│ [ 500                                  ]   │
│                                             │
│              [ Start Job ]                  │
│                                             │
│ Progress                                    │
│ █████████████████░░░  84%                   │
│                                             │
│ Businesses found: 421                       │
│ New businesses:   387                       │
│ Duplicates:        34                       │
│ Errors:             0                       │
│                                             │
│ [ Export CSV ]                              │
└─────────────────────────────────────────────┘
```

---

# Performance Expectations

The goal is not to match a commercial scraping platform purely on raw scale.

A local installation is intentionally different.

### Local application

```text
Your computer
      ↓
Browser
      ↓
Scraper
      ↓
SQLite
      ↓
CSV
```

### Commercial platform

```text
Cloud infrastructure
      ↓
Multiple workers
      ↓
Proxy infrastructure
      ↓
Browser fleet
      ↓
Distributed jobs
      ↓
Cloud storage
```

A local system can be excellent for normal prospecting workloads, but it should not be expected to provide unlimited cloud-scale throughput.

---

# Security

Do not commit:

```text
.env
*.db
data/
logs/
```

to Git.

Recommended `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc

.env

data/database/
data/exports/
data/logs/

.pytest_cache/
.idea/
.vscode/
```

---

# Testing

Run tests with:

```bash
pytest
```

Parser tests should use saved HTML fixtures rather than requiring a live browser every time.

Example:

```text
tests/
├── fixtures/
│   ├── business_1.html
│   └── business_2.html
│
├── test_parser.py
├── test_normalizer.py
├── test_deduplicator.py
└── test_exporter.py
```

This makes development faster and prevents unnecessary live requests during testing.

---

# Troubleshooting

## Playwright browser not installed

Run:

```bash
playwright install chromium
```

---

## Browser does not start

Check:

```bash
python --version
playwright --version
```

Then reinstall the browser:

```bash
playwright install --force chromium
```

---

## Missing business fields

This is expected occasionally.

The parser should treat fields as optional:

```python
phone = extract_phone() or None
website = extract_website() or None
```

Do not assume every business has every field.

---

## Duplicate businesses

Check the deduplication logic.

The preferred strategy is to use the strongest stable identifier available, followed by normalized URL, phone, website, and finally name/address combinations.

---

# Future Architecture

The eventual system should look like this:

```text
                         ┌───────────────┐
                         │ Search Config │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Search Engine │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Maps Collector│
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Data Parser   │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Normalization │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │    SQLite     │
                         └───────┬───────┘
                                 │
                   ┌─────────────┴─────────────┐
                   │                           │
                   ▼                           ▼
           ┌──────────────┐             ┌──────────────┐
           │  Enrichment  │             │ CSV Export   │
           └──────┬───────┘             └──────────────┘
                  │
                  ▼
           ┌──────────────┐
           │ Lead Scoring │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Qualified    │
           │ Leads        │
           └──────────────┘
```

---

# Philosophy

This project is deliberately designed around a few simple principles:

**The browser is an input mechanism, not the database.**

**CSV is an export format, not the source of truth.**

**Scraping is only the first step.**

**Data quality matters more than row count.**

**A reliable 500-lead dataset is more useful than an unreliable 10,000-row dump.**

The long-term objective is not to clone a commercial scraper feature-for-feature.

It is to build a **local lead-generation system that you control completely**.

---

# License

Choose an appropriate license before publishing this project publicly.

For private/internal use, a license file is not strictly necessary, but it is recommended if the repository may eventually become public.

---

# Status

**Early Development**

The architecture and interfaces are expected to evolve while the scraping, persistence, enrichment, and lead-scoring layers are implemented.
