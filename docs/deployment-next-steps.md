# Veritas Deployment & Next Steps

## Overview

**Goal:** Get Veritas live for demo, case study, and pilot outreach.

**Target URLs:**
- Frontend: `veritas.devbrew.ai` (Vercel)
- API: `veritas-api.onrender.com` (Render)
- Case Study: `devbrew.ai/case-studies/veritas`

---

## P0: Deployment (Must Do First)

### Backend - Render

| Step | Task | Notes |
|------|------|-------|
| 1 | Create Render account/project | render.com |
| 2 | Create PostgreSQL database | Free tier: 1GB storage |
| 3 | Create Web Service for API | Python 3.12, connect to GitHub |
| 4 | Configure build command | `cd apps/api && pip install -r requirements.txt` |
| 5 | Configure start command | `cd apps/api && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| 6 | Set environment variables | See below |
| 7 | Deploy and test `/health` | Verify API is responding |

**Environment Variables (Render):**
```
DATABASE_URL=<neon_connection_string>
ALLOWED_ORIGINS=https://veritas.devbrew.ai,http://localhost:3000
BETTER_AUTH_URL=https://veritas.devbrew.ai
DEBUG=false
```

### Database - Neon PostgreSQL

| Step | Task | Notes |
|------|------|-------|
| 1 | Create Neon account/project | neon.tech (free tier: 512MB) |
| 2 | Create database | Name: veritas |
| 3 | Get connection string | For Render env vars |
| 4 | Run migrations | `alembic upgrade head` |

### Frontend - Vercel

| Step | Task | Notes |
|------|------|-------|
| 1 | Create Vercel project | Connect GitHub repo |
| 2 | Set root directory | `apps/web` |
| 3 | Set environment variables | See below |
| 4 | Deploy | Verify build succeeds |
| 5 | Add custom domain | `veritas.devbrew.ai` |

**Environment Variables (Vercel):**
```
NEXT_PUBLIC_API_URL=https://veritas-api.onrender.com
DATABASE_URL=<same_neon_connection_string>
BETTER_AUTH_SECRET=<generate_random_string>
```

### Post-Deployment Verification

- [ ] API `/health` returns 200
- [ ] API `/docs` loads Swagger UI
- [ ] Frontend loads at custom domain
- [ ] Register new user works
- [ ] Login works
- [ ] Dashboard loads with auth
- [ ] Document upload works
- [ ] KYC results display correctly

---

## P1: Demo Readiness

### Demo Video Preparation

| Task | Notes |
|------|-------|
| Create test user account | compliance@demo.veritas.ai |
| Upload sample passport | Use clear, high-quality test image |
| Upload sample utility bill | Matching name to passport |
| Verify full flow works | Upload → Process → Results |
| Record 3-minute demo | Follow PRD demo script |

### Sample Data for Demo

Need realistic-looking but fake test documents:
- Passport (John Smith, US, clear MRZ)
- Utility bill (matching name/address)
- Business registration (for B2B demo)

### Monitoring Setup

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| UptimeRobot | Ping `/health` every 5 min | Yes |
| Sentry | Error tracking | Yes (5K events/mo) |
| Vercel Analytics | Frontend analytics | Built-in |

---

## P2: Case Study Page

### Content Needed

1. **Problem Statement**
   - Manual KYC pain points
   - Cost/time statistics

2. **Solution Overview**
   - What Veritas does
   - Tech stack highlights (OCR, ML, SHAP)

3. **Results/Metrics**
   - 95% faster (48 hrs → 4 sec)
   - 65% cost reduction
   - Consistent ML-based scoring

4. **Demo Video Embed**
   - 3-minute walkthrough

5. **Call to Action**
   - "Book a Pilot" button
   - Calendar link for calls

### Assets Needed

- [ ] Demo video (3 min)
- [ ] Screenshots of key screens
- [ ] Architecture diagram (optional)
- [ ] One-pager PDF (from PRD content)

---

## P3: Phase 2 Security (Should Do)

From the production readiness plan:

| Task | Priority | Notes |
|------|----------|-------|
| Magic number file validation | P1 | Verify file content matches extension |
| Expand rate limiting | P1 | Add to screening/risk endpoints |
| Environment variables cleanup | P1 | Remove hardcoded URLs |

---

## P4: Future Enhancements (Nice to Have)

- [ ] UI/UX improvements (see [ui-ux-improvements.md](./ui-ux-improvements.md))
- [ ] Audit logging for compliance
- [ ] GDPR features (data retention, export, deletion)
- [ ] Performance benchmarking
- [ ] Load testing for concurrent uploads

---

## Deployment Timeline

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1 | Render + Neon setup | API live |
| 1 | Vercel setup | Frontend live |
| 1 | DNS + verification | Full stack working |
| 2 | Demo data + testing | Demo-ready |
| 2 | Record demo video | 3-min video |
| 3 | Case study page | Live on DevBrew |

---

## Quick Commands Reference

```bash
# Local development
cd apps/api && uv run uvicorn main:app --reload --port 8000
cd apps/web && bun dev

# Build verification
cd apps/web && bun run build
cd apps/api && uv run pytest

# Database migrations
cd apps/api && uv run alembic upgrade head
```
