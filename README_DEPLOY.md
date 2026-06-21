Deployment notes
================

This repo contains the backend (FastAPI) and frontend (Next.js) components.

Quick steps to deploy:

- Backend: The repository includes a `Dockerfile` and `docker-compose.yml`. On push to `main`, GitHub Actions will build and publish a Docker image to GitHub Container Registry (`ghcr.io/${{ github.repository }}:latest`). Use that image to deploy on Render, Fly, Railway, or any container host.

- Frontend: A GitHub Actions workflow template is included to deploy to Vercel. Set `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` in GitHub Secrets to enable it.

Required environment variables (set in your host provider):

- GEMINI
- REDIS_URL
- UPLOAD_DIR
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- S3_BUCKET
- CLOUDINARY_URL (or CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
- GROQ (optional)
- GOOGLE_API_KEY (optional)
- PORT (platform provided)

Local testing:

Run web locally:

```powershell
$env:PORT=9001; $env:CELERY_TASK_ALWAYS_EAGER=1; .venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port $env:PORT
```

To run Redis and worker locally, use `docker compose up --build` (Docker required).
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
