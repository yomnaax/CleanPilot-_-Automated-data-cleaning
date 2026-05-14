# CleanPilot 🛸
### Intelligent Multi-Modal Data Cleaning Platform

> Graduation Project — Faculty of Computer Science & Artificial Intelligence, Nile University  
> Team: Yomna Khairy · Sama Eldesouky · Ziad Wael · Abdelrahman Abourayya · Karim Abdullah

---

## What is CleanPilot?

CleanPilot is an AI-powered data cleaning platform that automatically extracts cleaning rules from your datasets using a combination of statistical analysis and a local LLM (Large Language Model). Users can review, approve, or reject rules before applying them — giving full control over the cleaning process while leveraging AI to do the heavy lifting.

The system learns from user feedback over time. Every approval and rejection is stored in a vector database (ChromaDB) and used to improve future rule extractions on similar datasets — this is the RAG (Retrieval-Augmented Generation) feedback loop.

---

## How It Works

```
1. Upload your dataset (CSV, Excel, JSON, Parquet)
2. System profiles the data (nulls, types, outliers, distributions)
3. Statistical extractors + LLM extract cleaning rules
4. You review and approve/reject each rule
5. Apply approved rules → see before/after diff
6. Your decisions are stored → future extractions get smarter
```

---

## Features

### Current
- **Multi-domain rule extraction** — Finance, Healthcare, HR, Ecommerce, Education, Logistics, General
- **Domain-aware LLM prompting** — the model receives domain-specific constraints (e.g. age 0–100 for healthcare, credit scores 300–850 for finance)
- **Multiple rule types** — Range constraints, Categorical constraints, Regex patterns, Anomaly detection, Missing value rules, Uniqueness constraints, Functional dependencies
- **AI opinion on each rule** — LLM validates each extracted rule and explains whether it agrees or disagrees
- **RAG feedback loop** — approved/rejected rules stored as vectors in ChromaDB, retrieved to inform future extractions
- **Before/after diff view** — see exactly what changes before committing
- **User authentication** — JWT-based login/register, each user sees only their own datasets
- **Dark/light mode**
- **Change tracking** — full audit trail of cleaning decisions

### Planned (Future Work)
- Fine-tuned model (LoRA on Qwen2.5-3B) trained on collected feedback data
- Multi-tenancy with company roles (Admin, Company Admin, User)
- Text modality support — extract rules from unstructured text columns
- Image modality support — validate image columns (format, dimensions, corruption)
- Audio modality support — validate audio metadata columns
- httpOnly cookie auth (production security upgrade)
- Docker deployment
- API access for programmatic cleaning

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, Python 3.10+ |
| Database | SQLite (via SQLAlchemy) |
| Vector DB | ChromaDB |
| Embeddings | Sentence Transformers |
| LLM | Fine-tuned Qwen2.5-3B (LoRA) via Ollama — trained on domain-specific cleaning rules |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Data processing | Pandas, NumPy, Scikit-learn, Polars |

---

## Prerequisites

Make sure you have the following installed:

- **Python 3.10+**
- **Node.js 18+** and npm
- **Ollama** — for running the LLM locally

---

## Installation & Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/cleanpilot.git
cd cleanpilot
```

### 2. Install Ollama and pull the model

```bash
# Install Ollama (Mac)
brew install ollama

# Pull the model (about 2GB)
ollama pull qwen2.5:3b
```

### 3. Set up the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows

pip install -r app/requirements.txt
pip install "python-jose[cryptography]" "passlib[bcrypt]" email-validator bcrypt==4.0.1
```

### 4. Create the .env file

Create a file at `backend/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
LLM_PROVIDER=ollama
SECRET_KEY=your-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 5. Set up the frontend

```bash
cd frontend
npm install
```

---

## Running the App

You need **3 terminals** running simultaneously:

**Terminal 1 — Ollama:**
```bash
ollama serve
```

**Terminal 2 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --reload-exclude venv
```

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

---

## First Time Setup

1. Go to `http://localhost:3000`
2. Click **Create account** and register
3. Click **Upload Dataset** and upload a CSV file
4. Select the appropriate **domain** (Finance, Healthcare, etc.)
5. Click **Profile Dataset** to analyze the data
6. Click **Extract Rules** to run the LLM extraction
7. Review each rule — approve or reject with optional comments
8. Go to **Apply & Preview** to see the before/after diff
9. Apply rules to get your cleaned dataset

---

## Project Structure

```
cleanpilot/
├── backend/
│   └── app/
│       ├── api/          # FastAPI route handlers
│       ├── db/           # SQLAlchemy models and base
│       ├── services/     # Core logic
│       │   ├── llm/      # LLM client and prompts
│       │   ├── rag/      # ChromaDB indexer and retriever
│       │   └── rule_extractor/  # Statistical + LLM extractors
│       └── main.py
├── frontend/
│   └── src/
│       ├── api/          # API client
│       ├── components/   # Layout, shared components
│       ├── context/      # Auth context
│       └── pages/        # Dashboard, Upload, Rules, Cleaning
├── data/
│   ├── chroma_db/        # Vector database (auto-created)
│   └── storage/          # Uploaded datasets (auto-created)
└── rag_knowledge/        # Domain-specific rule templates
    ├── finance/
    └── ecommerce/
```

---

## API Documentation

Once the backend is running, visit:
```
http://localhost:8000/docs
```
for the full interactive Swagger API documentation.

---

## Notes

- The LLM runs **entirely locally** — no data is sent to any external service
- The database is a local SQLite file (`autoclean.db`) — no external DB needed
- ChromaDB is stored locally in `data/chroma_db/`
- All uploaded datasets are stored locally in `data/storage/`

---

## License

MIT License — see LICENSE file for details.
