# Skill Gap Analyzer

Upload your resume and a job description to see which skills you're missing and how to prioritize them. Supports Backend, Full Stack, and Cloud/DevOps roles.

**Stack:** React + TypeScript + Vite (frontend) · FastAPI (backend) · Supabase (auth) · Docker (deployment)

---

## Running locally

### Prerequisites
- Node.js 20+
- Python 3.11+

### 1. Environment

Copy `.env.example` to `.env` and fill in your values:

```env
VITE_ML_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn api_main:app --reload --port 8000
```

API runs at `http://localhost:8000` · Docs at `http://localhost:8000/docs`

### 3. Frontend

```bash
npm install
npm run dev
```

App runs at `http://localhost:5173`

---

## Auth setup (Supabase)

1. Create a project at [supabase.com](https://supabase.com)
2. Copy the **Project URL** and **anon key** from Settings → Data API into `.env`
3. To skip email confirmation during development: Authentication → Providers → Email → disable **Confirm email**

---

## Other commands

| Command | What it does |
|---|---|
| `npm run build` | Production frontend build |
| `npm run test` | Run frontend tests |
| `npm run typecheck` | TypeScript type check |
| `pytest` (in `backend/`) | Run backend tests |
