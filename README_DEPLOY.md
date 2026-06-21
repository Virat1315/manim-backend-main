Push and deploy instructions
===========================

1) Create GitHub repo and push local code

```bash
cd D:/pp/manim-backend-main
git init
git add .
git commit -m "Initial commit"
# create a repo on GitHub, then:
git remote add origin https://github.com/<your-org-or-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

2) Set required GitHub repo secrets (Repository Settings -> Secrets -> Actions):
- `VERCEL_TOKEN` — your Vercel Personal Token
- `VERCEL_ORG_ID` — your Vercel organization ID
- `VERCEL_PROJECT_ID` — the Vercel project ID for this backend
- `GEMINI` — your Gemini API key
- `REDIS_URL` — Redis connection string (e.g. redis://...)

3) Vercel project setup
- Create a new Project in Vercel and link the GitHub repo.
- In Vercel Project Settings -> Environment Variables, set the same variables (`GEMINI`, `REDIS_URL`, etc.) and set `Build & Output` if needed.

4) Frontend
- The frontend lives in a separate repository (`mentrax-frontend`). Push that repo to GitHub and either:
  - Link it in Vercel (recommended) via the Vercel UI, or
  - Use a similar GitHub Action with `vercel --prod` in that repo.

5) Local testing
- Run backend locally:
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
- Run frontend locally in its repository:
```bash
cd path/to/mentrax-frontend
npm install
npm run dev
```

Notes
- Vercel serverless functions are short-lived; this backend depends on Celery/Redis and long-running workers which are not suited for Vercel Functions. Consider deploying backend to Railway/Render/Heroku or use Docker on a host if Celery is required.
