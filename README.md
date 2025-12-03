# Automated Insight Engine

An AI-powered data analysis and reporting platform that transforms raw data from **multiple sources (CSV, SQL, Databases)** into actionable business insights with downloadable PowerPoint presentations, **QR-linked live dashboards**, and **AI-generated voice briefings**.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Gemini](https://img.shields.io/badge/Google-Gemini%202.0-orange.svg)
![Murf AI](https://img.shields.io/badge/Murf-TTS%20Voice-purple.svg)

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Solution Approach](#-solution-approach)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [System Architecture](#-system-architecture)
- [Data Sources](#-data-sources)
- [Methodology](#-methodology)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Configuration Guide](#-configuration-guide)
- [Sample Output](#-sample-output)
- [Roadmap](#-roadmap)

---

##  Problem Statement

**Challenge:** Organizations collect vast amounts of performance data (marketing campaigns, sales, web analytics) but struggle to:

1. **Extract meaningful insights** from raw data across multiple sources
2. **Compare performance** across time periods (week-over-week, month-over-month)
3. **Identify key drivers** of change and their business impact
4. **Communicate findings** effectively to stakeholders
5. **Automate reporting** to save analyst time
6. **Bridge the gap** between static reports and live data
7. **Consume insights on-the-go** without reading lengthy reports

**Need:** An automated system that can ingest data from **multiple sources**, compute KPIs, identify significant changes, generate AI-powered narratives, produce professional reports with **live dashboard access**, and provide **audio summaries**—all with minimal manual intervention.

---

##  Solution Approach

### Design Philosophy

1. **Multi-Source Ingestion:** Accept data from CSV files, SQL databases, and various database systems
2. **Configuration-Driven:** All analysis parameters defined in YAML—no code changes needed
3. **Modular Architecture:** Each component (ingestion, metrics, insights, narrative, report) is independent and reusable
4. **Graceful Degradation:** System works even without AI API keys (fallback narratives)
5. **Static + Live Bridge:** QR codes link static reports to live dashboards
6. **Accessibility:** Voice briefings for consuming insights hands-free

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Polars over Pandas** | 10-100x faster for large datasets, better memory efficiency |
| **DuckDB for joins** | SQL-based joins are more intuitive, handles complex multi-source joins |
| **SQLAlchemy for DB connections** | Unified interface for PostgreSQL, MySQL, SQLite, SQL Server |
| **YAML configuration** | Human-readable, version-controllable, no code changes for new analyses |
| **Impact scoring** | Quantitative ranking ensures most important insights surface first |
| **Structured LLM prompts** | JSON schema enforcement produces consistent, parseable outputs |
| **QR code on final slide** | Seamless transition from static report to live data exploration |
| **Murf AI for TTS** | Professional-quality voice briefings for mobile consumption |

---

##  Key Features

###  Multi-Source Data Ingestion
- **CSV Files:** Direct file upload or path reference
- **SQL Databases:** PostgreSQL, MySQL, SQLite, SQL Server via SQLAlchemy
- **Cloud Databases:** BigQuery, Snowflake, Redshift (coming soon)
- **Data Warehouses:** Connect to existing enterprise data infrastructure

###  Intelligent Analysis
- **Derived Metrics:** Compute CTR, CPC, ROAS, and custom KPIs from raw data
- **Period Comparison:** Automatic week-over-week, month-over-month analysis
- **Impact Scoring:** Rank insights by business significance
- **Dimension Drill-down:** Analyze by campaign, geo, product, or any dimension

###  AI-Powered Narrative Generation
- **Google Gemini 2.0 Flash:** Primary LLM for narrative generation
- **OpenAI GPT-4.1:** Alternative LLM support
- **Structured Output:** Consistent JSON format for headlines, bullets, recommendations
- **Fallback Mode:** Rule-based narratives when API is unavailable

###  Professional PowerPoint Reports
- **Branded Slides:** Customizable title, body, and table slides
- **Data Tables:** Ranked insights with color-coded performance indicators
- **Executive Summary:** AI-generated headline and key findings
- **Actionable Recommendations:** Data-driven next steps

###  QR Code Integration 
- **Live Dashboard Access:** QR code on the final slide links to a private web dashboard
- **Secure Access:** Dashboard only accessible via the QR code (no public URL)
- **Real-time Data:** View live data updates without regenerating the report
- **Mobile-Friendly:** Scan from phone to view dashboard on-the-go
- **Session-Based:** Each report generates a unique dashboard session

###  Voice Briefing 
- **AI Voice Synthesis:** Powered by Murf AI's Text-to-Speech API
- **30-Second Summary:** Concise audio overview of key insights
- **MP3 Download:** Audio file alongside PPTX for mobile playback
- **Hands-Free Consumption:** Perfect for listening during commute or before meetings
- **Professional Quality:** Natural-sounding AI voices

###  Web Dashboard 
- **QR-Gated Access:** Private dashboard accessible only via QR code link
- **Interactive Charts:** Visualize trends and comparisons
- **Drill-Down Analysis:** Explore data by any dimension
- **Export Options:** Download data in various formats
- **Real-Time Sync:** Reflects latest data when accessed

---

## 🛠 Technology Stack

### Core Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Core programming language |
| **FastAPI** | 0.104+ | Async REST API framework |
| **Uvicorn** | 0.24+ | ASGI server |
| **Pydantic** | 2.0+ | Data validation and settings management |

### Data Processing
| Technology | Version | Purpose |
|------------|---------|---------|
| **Polars** | 0.19+ | High-performance DataFrame operations |
| **DuckDB** | 0.9+ | In-process SQL database for complex joins |
| **SQLAlchemy** | 2.0+ | Database connection and ORM |
| **PyYAML** | 6.0+ | YAML configuration parsing |
| **Connectorx** | 0.3+ | Fast database connector for Polars |

### Database Connectors
| Database | Connector | Status |
|----------|-----------|--------|
| **PostgreSQL** | psycopg2 | ✅ Supported |
| **MySQL** | mysql-connector | ✅ Supported |
| **SQLite** | Built-in | ✅ Supported |
| **SQL Server** | pyodbc | ✅ Supported |

### AI/ML Integration
| Technology | Version | Purpose |
|------------|---------|---------|
| **Google Generative AI** | 0.3+ | Gemini 2.0 Flash for narrative generation |
| **OpenAI** | 1.3+ | GPT-4.1-mini (alternative LLM) |
| **Murf AI** | API v1 | Text-to-Speech for voice briefings |

### Report Generation
| Technology | Version | Purpose |
|------------|---------|---------|
| **python-pptx** | 0.6+ | PowerPoint presentation creation |
| **qrcode** | 7.4+ | QR code generation for dashboard access |
| **Pillow** | 10.0+ | Image processing for QR codes |
| **Matplotlib** | 3.8+ | Chart generation (optional) |

### Frontend & Dashboard
| Technology | Purpose |
|------------|---------|
| **HTML5/CSS3** | Modern responsive UI |
| **Vanilla JavaScript** | No framework dependencies |
| **Chart.js** | Interactive dashboard charts |
| **Fetch API** | Async file uploads |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (HTML/JS)                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ File Upload │  │Config Editor│  │Progress View│  │ Download Reports + MP3  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                │                     │
          ▼                ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI REST API                                   │
│  POST /generate-report    GET /health    GET /static/reports/*                  │
│  GET /dashboard/{session} (QR-gated)                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               DATA INGESTION                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                      │
│  │     CSV      │    │     SQL      │    │   DATABASE   │                      │
│  │   (Files)    │    │  (Queries)   │    │ (PostgreSQL, │                      │
│  │              │    │              │    │ MySQL, etc.) │                      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                      │
│         │                   │                   │                               │
│         └───────────────────┼───────────────────┘                               │
│                             ▼                                                   │
│                    ┌────────────────┐                                          │
│                    │ Polars/DuckDB  │                                          │
│                    │ Unified Layer  │                                          │
│                    └────────┬───────┘                                          │
└─────────────────────────────┼───────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ENGINE PIPELINE                                    │
│                                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                      │
│  │   METRICS    │───▶│   INSIGHTS   │───▶│     LLM      │                      │
│  │  (Derived    │    │  (Deltas +   │    │  (Gemini/    │                      │
│  │   KPIs)      │    │   Ranking)   │    │   OpenAI)    │                      │
│  └──────────────┘    └──────────────┘    └──────────────┘                      │
│                                                 │                               │
│                    ┌────────────────────────────┼────────────────────────────┐  │
│                    ▼                            ▼                            ▼  │
│          ┌──────────────┐            ┌──────────────┐            ┌───────────┐ │
│          │   REPORT     │            │ VOICE BRIEF  │            │ DASHBOARD │ │
│          │  (python-    │            │  (Murf AI    │            │  (Web +   │ │
│          │   pptx)      │            │   TTS)       │            │   QR)     │ │
│          └──────┬───────┘            └──────┬───────┘            └─────┬─────┘ │
│                 │                           │                          │       │
│                 ▼                           ▼                          ▼       │
│  ┌────────────────────────────────────────────────────────────────────────────┐│
│  │                          OUTPUT FILES                                      ││
│  │  📊 report.pptx    🎙️ briefing.mp3    📱 QR → dashboard/{session}          ││
│  └────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Data Sources

### CSV Files
```yaml
sources:
  clicks:
    type: csv
    path: "data/clicks.csv"
    date_col: "date"
    dimensions: [campaign, geo]
    metrics: [impressions, clicks, spend]
```

### SQL Query
```yaml
sources:
  sales_data:
    type: sql
    connection_string: "postgresql://user:pass@host:5432/db"
    query: |
      SELECT date, product, region, revenue, units_sold
      FROM sales
      WHERE date >= '2025-01-01'
    date_col: "date"
    dimensions: [product, region]
    metrics: [revenue, units_sold]
```

### Database Table
```yaml
sources:
  marketing_spend:
    type: database
    connection:
      driver: mysql
      host: "localhost"
      port: 3306
      database: "marketing"
      username: "${DB_USER}"      # Environment variable
      password: "${DB_PASSWORD}"
    table: "ad_spend"
    date_col: "spend_date"
    dimensions: [channel, campaign_type]
    metrics: [spend, conversions, revenue]
```

### Multiple Sources with Join
```yaml
dataset:
  primary_source: clicks
  sources:
    clicks:
      type: csv
      path: "data/clicks.csv"
      join_key: [campaign, date]
    
    conversions:
      type: sql
      connection_string: "postgresql://..."
      query: "SELECT * FROM conversions"
      join_key: [campaign, date]
  
  join_type: left  # left, right, inner, outer
```

---

##  Methodology

### Phase 1: Multi-Source Data Ingestion
```
CSV / SQL / Database → Polars DataFrames → DuckDB Join → Unified DataFrame
```

1. **Detect Source Type:** Determine if source is CSV, SQL query, or database table
2. **Load Data:**
   - CSV: `polars.read_csv()` with schema inference
   - SQL: `polars.read_database()` via connectorx or SQLAlchemy
   - Database: Build query from table name, execute via connector
3. **Schema Validation:** Verify required columns exist (date, dimensions, metrics)
4. **Multi-Source Join:** Use DuckDB SQL for complex joins, Polars as fallback
5. **Output:** Single unified DataFrame with all data

### Phase 2: Metrics Computation
```
Raw Metrics → Derived KPIs → Period Split → Aggregated Data
```

1. **Parse Dates:** Convert date column to proper Date type
2. **Compute Derived Metrics:** Apply formulas from config (e.g., `ctr = clicks / impressions`)
3. **Split Periods:** Separate data into CURRENT and PREVIOUS time ranges
4. **Aggregate:** Group by dimensions, sum metrics

### Phase 3: Insight Generation
```
Current vs Previous → Delta Calculation → Impact Scoring → Ranked Insights
```

1. **Join Periods:** Match current/previous by dimension values
2. **Calculate Deltas:**
   - `delta = current_value - previous_value`
   - `delta_pct = (delta / previous_value) * 100`
3. **Compute Impact Score:**
   ```
   impact_score = |delta| × (1 + pct_factor) × (1 + priority_weight)
   ```
4. **Rank:** Sort by impact_score descending, return top N

### Phase 4: Narrative Generation
```
Insights JSON → LLM Prompt → Structured Response → Narrative Object
```

1. **Build Prompt:** Format top insights with context into structured prompt
2. **Call LLM:** Send to Gemini 2.0 Flash (or OpenAI GPT-4.1-mini)
3. **Parse Response:** Extract JSON with title, headline, bullets, recommendation
4. **Fallback:** If LLM fails, generate rule-based narrative

### Phase 5: Voice Briefing Generation (NEW)
```
Narrative → Text Script → Murf AI TTS → MP3 Audio File
```

1. **Generate Script:** Convert narrative to natural speech text (~150 words for 30 sec)
2. **Call Murf AI:** Send text to TTS API with voice settings
3. **Receive Audio:** Get MP3 audio stream
4. **Save File:** Store alongside PPTX with matching filename

### Phase 6: Report Generation with QR Code (NEW)
```
Narrative + Insights → PPTX Slides → QR Code → Dashboard Session → Saved Files
```

1. **Create Presentation:** 16:9 widescreen format
2. **Add Slides:**
   - Cover slide (title, period, date)
   - Headline slide (key finding)
   - Bullets slide (detailed insights)
   - Insights table (ranked metrics)
   - Recommendation slide (action items)
   - **QR Code slide (NEW):** Links to private dashboard
3. **Generate Dashboard Session:** Create unique session ID for this report
4. **Create QR Code:** Encode dashboard URL with session token
5. **Embed QR:** Add QR code image to final slide
6. **Save:** Write PPTX and MP3 to `static/reports/`
7. **Return:** Provide download URLs for both files

---

## 📱 QR Code & Dashboard System

### How It Works

1. **Report Generation:** When a report is created, a unique session ID is generated
2. **QR Code Creation:** A QR code is embedded on the final slide containing:
   ```
   https://your-domain.com/dashboard/{session_id}?token={access_token}
   ```
3. **Scanning:** User scans QR code with phone camera
4. **Authentication:** Session token validates access (no login required)
5. **Dashboard:** Interactive web dashboard displays live data

### Security Model

- **No Public URL:** Dashboard endpoints are not discoverable
- **Session-Based:** Each report has a unique, non-guessable session ID
- **Token Validation:** Access token required in URL (embedded in QR)
- **Expiration:** Sessions expire after configurable period (default: 30 days)
- **Audit Trail:** Dashboard access is logged for analytics

### Dashboard Features

-  Interactive trend charts
-  Drill-down by dimensions
-  Comparison views (current vs previous)
-  Data export (CSV, Excel)
-  Refresh for latest data

---

##  Voice Briefing System

### Murf AI Integration

```python
# Voice briefing generation flow
narrative = {
    "headline": "Campaign performance improved 30%...",
    "bullets": ["Performance Max grew 30%...", ...],
    "recommendation": "Increase budget for..."
}

# Generate 30-second script
script = generate_voice_script(narrative)  # ~150 words

# Call Murf AI TTS
audio = murf_api.synthesize(
    text=script,
    voice="en-US-marcus",  # Professional male voice
    speed=1.0,
    format="mp3"
)

# Save audio file
save_path = "static/reports/briefing_20251203_123456.mp3"
```

### Voice Options

| Voice | Language | Style |
|-------|----------|-------|
| Marcus | en-US | Professional, authoritative |
| Julia | en-US | Warm, approachable |
| James | en-GB | British, formal |
| Emma | en-GB | British, friendly |

### Use Cases

-  Listen during commute to client meeting
-  Quick refresh before presentations
-  Accessibility for visually impaired users
-  Time-constrained stakeholder updates

---

## 📁 Project Structure

```
automated-insight-engine/
│
├── backend/                      # Python backend
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI application & endpoints
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── ingest.py            # Multi-source data loading
│   │   ├── metrics.py           # KPI calculation & period splitting
│   │   ├── insights.py          # Delta computation & ranking
│   │   ├── narrative.py         # LLM integration (Gemini/OpenAI)
│   │   ├── voice.py             # Murf AI TTS integration (NEW)
│   │   ├── qrcode_gen.py        # QR code generation (NEW)
│   │   ├── dashboard.py         # Dashboard session management (NEW)
│   │   └── report_pptx.py       # PowerPoint generation
│   │
│   └── core/
│       ├── __init__.py
│       ├── config.py            # YAML parsing & validation
│       ├── database.py          # Database connection manager (NEW)
│       └── logger.py            # Logging configuration
│
├── frontend/
│   ├── index.html               # Main upload UI
│   └── dashboard/               # Dashboard web app (NEW)
│       ├── index.html
│       ├── charts.js
│       └── styles.css
│
├── data/                        # Sample data files
│   └── clicks.csv               # Example marketing data
│
├── static/
│   └── reports/                 # Generated PPTX + MP3 files
│
├── tmp/                         # Temporary files
│
├── config.yaml                  # Example configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

##  Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Google Gemini API key (free tier available)
- Murf AI API key (for voice briefings)

### Step 1: Clone Repository

```bash
git clone https://github.com/anubhav-n-mishra/groundtruth-ai-hackathon.git
cd groundtruth-ai-hackathon
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set API Keys

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY = "your-gemini-api-key"
$env:MURF_API_KEY = "ap2_8579ad9f-8338-4aa2-96ff-498873a3037b"

# macOS/Linux
export GEMINI_API_KEY="your-gemini-api-key"
export MURF_API_KEY="ap2_8579ad9f-8338-4aa2-96ff-498873a3037b"
```

### API Key Sources

| Service | Get API Key | Purpose |
|---------|-------------|---------|
| **Google Gemini** | [aistudio.google.com](https://aistudio.google.com/app/apikey) | Narrative generation |
| **Murf AI** | [murf.ai](https://murf.ai) | Voice briefing TTS |

---

## 📖 Usage

### Start the Server

```bash
# From project root
uvicorn backend.app.main:app --reload --port 8000
```

### Access the Application

| Interface | URL |
|-----------|-----|
| **Frontend UI** | http://localhost:8000/frontend/ |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **API Docs (ReDoc)** | http://localhost:8000/redoc |
| **Dashboard** | Via QR code only |

### Quick Test

1. Open http://localhost:8000/frontend/
2. Upload the included `config.yaml` (or use sample)
3. Click "Generate Report"
4. Download the generated PPTX and MP3
5. Scan QR code on final slide to access dashboard

---

## 📡 API Reference

### Generate Report

**Endpoint:** `POST /generate-report`

**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST "http://localhost:8000/generate-report" \
  -F "config_file=@config.yaml"
```

**Response:**
```json
{
  "download_url": "/static/reports/insight_report_20251203_112830_abc123.pptx",
  "audio_url": "/static/reports/briefing_20251203_112830_abc123.mp3",
  "dashboard_url": "/dashboard/abc123def456",
  "message": "Report generated successfully"
}
```

### Access Dashboard (QR-Gated)

**Endpoint:** `GET /dashboard/{session_id}`

**Note:** Requires valid token in query parameter (embedded in QR code)

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "ok"
}
```

---

## 📝 Configuration Guide

### Full Configuration Schema

```yaml
# Dataset configuration
dataset:
  primary_source: clicks
  sources:
    # CSV source
    clicks:
      type: csv
      path: "data/clicks.csv"
      date_col: "date"
      dimensions:
        - campaign
        - geo
      metrics:
        - impressions
        - clicks
        - spend
    
    # SQL source
    conversions:
      type: sql
      connection_string: "postgresql://user:pass@localhost:5432/analytics"
      query: |
        SELECT campaign, date, conversions, revenue
        FROM conversion_data
        WHERE date >= '2025-01-01'
      date_col: "date"
      dimensions: [campaign]
      metrics: [conversions, revenue]
      join_key: [campaign, date]
    
    # Database table source
    costs:
      type: database
      connection:
        driver: mysql
        host: "db.example.com"
        port: 3306
        database: "finance"
        username: "${DB_USER}"
        password: "${DB_PASSWORD}"
      table: "marketing_costs"
      date_col: "cost_date"
      dimensions: [campaign]
      metrics: [cost]
      join_key: [campaign]

# Derived metrics (calculated from base metrics)
derived_metrics:
  ctr: "clicks / impressions"
  cpc: "spend / clicks"
  roas: "revenue / spend"
  cpa: "spend / conversions"

# Report configuration
report:
  primary_date_col: date
  
  comparison:
    current_start: "2025-11-24"
    current_end: "2025-11-30"
    previous_start: "2025-11-17"
    previous_end: "2025-11-23"
  
  primary_dims:
    - campaign
    - geo
  
  kpi_priority:
    - roas
    - ctr
    - cpc
    - impressions

# Voice briefing settings (NEW)
voice:
  enabled: true
  provider: murf
  voice_id: "en-US-marcus"
  duration_target: 30  # seconds

# Dashboard settings (NEW)
dashboard:
  enabled: true
  session_expiry_days: 30
  theme: "dark"
```

---

## 📊 Sample Output

### Generated Files

| File | Description |
|------|-------------|
| `insight_report_20251203_112830.pptx` | PowerPoint with insights + QR code |
| `briefing_20251203_112830.mp3` | 30-second audio summary |

### QR Code Slide Preview

```
┌─────────────────────────────────────────────┐
│                                             │
│            📱 Scan for Live Dashboard       │
│                                             │
│               ┌───────────┐                 │
│               │ █▀▀▀▀▀▀█ │                 │
│               │ █ QR   █ │                 │
│               │ █ CODE █ │                 │
│               │ █▄▄▄▄▄▄█ │                 │
│               └───────────┘                 │
│                                             │
│    Access real-time data and insights       │
│    Valid until: January 2, 2026             │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Google Gemini API key |
| `OPENAI_API_KEY` | - | OpenAI API key (alternative) |
| `MURF_API_KEY` | - | Murf AI TTS API key |
| `INSIGHT_ENGINE_LLM_PROVIDER` | `auto` | LLM provider: `gemini`, `openai`, `auto` |
| `INSIGHT_ENGINE_LLM_MODEL` | `gemini-2.0-flash` | Model name |
| `INSIGHT_ENGINE_REPORTS_DIR` | `static/reports` | Output directory |
| `INSIGHT_ENGINE_LOG_LEVEL` | `INFO` | Logging level |
| `DB_USER` | - | Database username (for SQL sources) |
| `DB_PASSWORD` | - | Database password (for SQL sources) |

---



## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: polars` | Run `pip install polars` |
| `GEMINI_API_KEY not set` | Set environment variable before running |
| `MURF_API_KEY not set` | Voice briefing will be skipped |
| `File not found: data/xyz.csv` | Check path in config.yaml |
| Port 8000 in use | Use `--port 8001` |
| Database connection failed | Verify connection string and credentials |

---

## 📄 License

MIT License - Free for personal and commercial use.

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

Built with ❤️ Anubhav Mishra

**Repository:** [github.com/anubhav-n-mishra/groundtruth-ai-hackathon](https://github.com/anubhav-n-mishra/groundtruth-ai-hackathon)
