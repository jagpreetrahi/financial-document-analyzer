# Financial Document Analyzer - Debug Assignment

## Project Overview
A comprehensive financial document analysis system that processes corporate reports, financial statements, and investment documents using AI-powered analysis agents.


## Bugs Found and Fixed

### `requirements.txt` — Dependency Conflicts

| # | Bug | Fix |
|---|-----|-----|
| 1 | `onnxruntime==1.18.0` conflicts with crewai needing `1.22.0` | Changed to `onnxruntime==1.22.0` |
| 2 | `google-api-core==2.10.0` is blacklisted by multiple google packages | Changed to `google-api-core==2.15.0` |
| 3 | All opentelemetry packages at `1.25.0` conflict with crewai needing `>=1.30.0` | Upgraded all to `1.30.0` and instrumentation to `0.51b0` |
| 4 | `protobuf==4.25.3` conflicts with `opentelemetry-proto==1.30.0` needing `>=5.0` | Changed to `protobuf==5.27.0` |
| 5 | `openai==1.30.5` conflicts with `litellm==1.72.0` needing `>=1.68.2` | Changed to `openai==1.68.2` |
| 6 | `langsmith==0.1.67` conflicts with `embedchain` (crewai transitive dep) | Removed manual pin, let crewai resolve |
| 7 | `langchain-core==0.1.52` conflicts with modern pydantic requirements | Removed manual pin, let crewai resolve |
| 8 | `pydantic==2.6.1` too old for langchain-core needing `>=2.7.4` | Changed to `pydantic>=2.7.4` |
| 9 | All Google packages manually pinned causing cascade conflicts | Removed all — crewai installs compatible versions automatically |
| 10 | `pip==24.0` pinned — never pin pip in requirements | Removed |
| 11 | Missing `uvicorn` and `python-multipart` needed to run FastAPI | Added both |

---

### `main.py` — Deterministic Bugs

| # | Bug | Fix |
|---|-----|-----|
| 1 | `import asyncio` — imported but never used | Removed |
| 2 | `uvicorn.run(app, host="0.0.0.0", port=8000, "main:app")` — positional arg after keyword args, SyntaxError | Changed to `uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)` |
| 3 | Endpoint function named `analyze_financial_document` — same as imported task, overwrites import | Renamed endpoint to `analyze_document` |
| 4 | `file_path` passed to `run_crew()` but never included in `kickoff()` inputs | Added `'file_path': file_path` to kickoff inputs dict |
| 5 | Crew only had 1 agent and 1 task | Updated to include all 4 agents and all 4 tasks |

---

### `agents.py` — Deterministic Bugs and Inefficient Prompts

| # | Bug | Fix |
|---|-----|-----|
| 1 | `llm = llm` — self-assignment NameError on startup | Replaced with `ChatOpenAI(model=..., api_key=...)` from `.env` |
| 2 | `from crewai.agents import Agent` — wrong import path | Changed to `from crewai import Agent` |
| 3 | `tool=[...]` — wrong parameter name | Changed to `tools=[...]` |
| 4 | `max_iter=1` on all agents — gives up after one attempt | Changed to `max_iter=5` |
| 5 | `max_rpm=1` on all agents — causes timeouts | Changed to `max_rpm=10` |
| 6 | `allow_delegation=True` on financial_analyst — no agents to delegate to | Changed to `False` |
| 7 | All agent goals and backstories instruct AI to fabricate advice and fake credentials | Replaced with accurate, regulation-compliant, evidence-based prompts |

**Inefficient Prompts Fixed:**
- `financial_analyst` — was told to "make up investment advice". Now instructs strict evidence-based analysis with document citations.
- `verifier` — was told to "say yes to everything". Now performs structured document validation.
- `investment_advisor` — was told to "sell expensive products". Now provides balanced, risk-disclosed recommendations.
- `risk_assessor` — was told "YOLO through the volatility". Now uses standard risk frameworks with balanced ratings.

---

### `tools.py` — Deterministic Bugs

| # | Bug | Fix |
|---|-----|-----|
| 1 | `from crewai_tools import tools` — unused, doesn't exist | Removed |
| 2 | `Pdf` class never imported — NameError at runtime | Replaced with `PyPDFLoader` from langchain |
| 3 | All methods missing `self` parameter | Added `@staticmethod` decorator |
| 4 | No `@tool` decorator — CrewAI cannot use the functions | Added `@tool("name")` to all methods |
| 5 | All methods `async def` — CrewAI doesn't support async tools | Changed all to regular `def` |
| 6 | No type hints on parameters — required by CrewAI | Added `str` type hints |
| 7 | No error handling in PDF reader | Added try/except |
| 8 | `RiskTool` and `InvestmentTool` returned placeholder strings | Implemented actual keyword extraction and data structuring logic |

---

### `task.py` — Deterministic Bugs and Inefficient Prompts

| # | Bug | Fix |
|---|-----|-----|
| 1 | All 4 tasks assigned to `financial_analyst` — specialist agents never used | Each task now assigned to its correct agent |
| 2 | No `context` between tasks — each task starts blind | Tasks now chain: each passes output as context to the next |
| 3 | `{file_path}` missing from task descriptions | Added to all relevant task descriptions |
| 4 | `verifier` agent imported but never assigned to any task | Now correctly assigned to `verification` task |
| 5 | All task descriptions instruct agents to fabricate data and fake URLs | Replaced with precise, structured, compliance-aware descriptions |
| 6 | `expected_output` fields encourage contradictions and jargon | Replaced with structured output templates requiring cited evidence |

---

## Setup and Instruction

### Prerequisites

- Python 3.11+
- OpenAI API key
- Serper API key (for web search)
- Docker (for Redis — required for queue worker bonus)

### Step 1: Clone the repository

```bash
git clone 
cd financial-document-analyzer
```

### Step 2: Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set up environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-openai-key-here
SERPER_API_KEY=your-serper-key-here
MODEL=gpt-4o-mini
REDIS_URL=redis://localhost:6379/0
```

### Step 5: Add your financial document

The project is pre-configured for Tesla Q2 2025:
```
data/
└── TSLA-Q2-2025-Update.pdf
```

Download from: https://www.tesla.com/sites/default/files/downloads/TSLA-Q2-2025-Update.pdf

Or upload any financial PDF via the API.

### Step 6: Start Redis (for queue worker)

```bash
docker run -d -p 6379:6379 redis:alpine
```

### Step 7: Start Celery worker (in a separate terminal)

```bash
# Activate venv first
venv\Scripts\activate

# Start worker
celery -A celery_worker worker --loglevel=info --concurrency=4
```

### Step 8: Run the FastAPI server (in another terminal)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You now have:
- API server at: `http://localhost:8000`
- Swagger docs at: `http://localhost:8000/docs`
- Flower dashboard (optional): `celery -A celery_worker flower --port=5555`

---

## Usage Instructions

### Async Queue (recommended)

```bash
# Step 1: Submit document — returns task_id immediately
curl -X POST "http://localhost:8000/analyze/async" \
  -F "file=@data/TSLA-Q2-2025-Update.pdf" \
  -F "query=What are the key investment opportunities?"

# Response:
# {"status": "queued", "task_id": "abc-123", "poll_url": "/result/abc-123"}

# Step 2: Poll for result
curl "http://localhost:8000/result/abc-123"
```

### Synchronous (simple, blocking)

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@data/TSLA-Q2-2025-Update.pdf" \
  -F "query=Analyze this for investment insights"
```

# API Documentation

### `GET /`
Health check.

**Response:**
```json
{"message": "Financial Document Analyzer API is running", "version": "2.0.0"}
```

---

### `POST /analyze`
Synchronous analysis — blocks until complete (1-3 minutes).

**Request:** `multipart/form-data`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | PDF | Yes | Financial document |
| `query` | string | No | Analysis question |

**Response (200):**
```json
{
  "status": "success",
  "query": "...",
  "analysis": "Full analysis...",
  "file_processed": "TSLA-Q2-2025-Update.pdf"
}
```

---

### `POST /analyze/async`
Queue document for async processing — returns immediately.

**Request:** `multipart/form-data` (same as above)

**Response (202):**
```json
{
  "status": "queued",
  "task_id": "abc-123-def-456",
  "message": "Document queued for analysis",
  "poll_url": "/result/abc-123-def-456",
  "file_queued": "TSLA-Q2-2025-Update.pdf"
}
```

---

### `GET /result/{task_id}`
Poll for async task result.

**Response by status:**

```json
// PENDING
{"task_id": "...", "status": "pending", "message": "Task is waiting in queue"}

// PROGRESS  
{"task_id": "...", "status": "processing", "message": "Running financial analysis", "progress": "50%"}

// SUCCESS
{"task_id": "...", "status": "completed", "result": {"status": "success", "analysis": "..."}}

// FAILURE
{"task_id": "...", "status": "failed", "error": "Error message"}
```

---

### `GET /queue/status`
Check Redis queue health and worker status.

**Response:**
```json
{
  "status": "redis_connected",
  "active_tasks": 2,
  "queued_tasks": 5,
  "workers": ["celery@hostname"]
}
```

---



