# DigiPlus AI-Powered Service Desk 🤖🎫

A clean, modern, and intelligent IT Service Desk web application built for the **DigiPlus Technical Assessment**. The application assists support engineers in triaging natural language incident descriptions, generating automated AI root-cause diagnostics, matching relevant technical knowledge-base runbooks, and recording incident resolutions with persistent SQLite storage.

---

## 🌟 Key Features

## Main Features

### 1. Dashboard
- Shows total, open, in-progress, and resolved incidents.
- Displays recent incidents.
- Shows incident priority and category summaries.

### 2. Ticket Management
- Create tickets with title, description, priority, and category.
- Search and filter tickets.
- Move tickets through Open, In Progress, Resolved, and Closed.
- Add root cause and resolution details.

### 3. AI Incident Analysis
- Analyze incidents using Google Gemini.
- Generates a short summary, possible root cause, and suggested solution.
- Recommends the appropriate priority and category.
- Allows AI-generated solutions to be copied into the resolution notes.

### 4. Knowledge Base
- Includes support guides for common technical issues.
- Shows relevant guides based on the incident.
- Allows engineers to view and copy troubleshooting steps.

### 5. Data Storage
- Uses SQLite to store incidents and knowledge-base data.
- Data remains available after refreshing or restarting the application.
- Includes sample incidents and support guides.

### 6. Curated Seed Datasets & Evaluation Harness (Phase 0)
- **Dataset Notice:** The seed datasets and evaluation golden sets are **synthetic, production-style curated IT helpdesk datasets** designed for benchmarking retrieval precision and LLM incident resolution.
- **`data/seed/kb_articles.jsonl`**: 40 canonical technical runbooks covering 8 key categories (`network`, `email`, `VPN and access`, `hardware`, `software installation`, `account and password`, `database`, `performance`).
- **`data/seed/tickets.jsonl`**: 300 realistic historical incident tickets with verified resolutions and category mappings.
- **`eval/golden_set.jsonl`**: 60 held-out evaluation tickets strictly excluded from the searchable index to avoid benchmark contamination.
- **Regenerate Seed Datasets:**
  ```bash
  python scripts/generate_seed_data.py --seed 42
  ```
- **Load Seed Datasets:**
  ```bash
  python scripts/load_seed.py --db-type sqlite
  ```
- **Run Dataset Unit Tests:**
  ```bash
  python -m pytest tests/test_seed_data.py -v
  ```

## 🚀 Quick Start Guide

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+ or v20+ / v22+ recommended)
- `npm` (bundled with Node.js)

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure AI API Key (Optional)
Copy the example environment file:
```bash
cp .env.example .env.local
```

Edit `.env.local` and add your **Google Gemini API Key**:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```
> 💡 *Note: If no API key is provided, the application automatically uses an intelligent built-in heuristic diagnostic engine matching HuggingFace help-desk datasets, so the application remains 100% functional out-of-the-box.*

### 3. Run the Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Production Build & Test
```bash
npm run build
npm run start
```

---

## 🧪 Automated End-to-End Testing

To run the automated verification script testing the entire incident lifecycle (Ticket Creation ➡️ AI Analysis ➡️ Runbook Matching ➡️ Resolution ➡️ Dashboard Stats):

```bash
node test-e2e.mjs
```

---

