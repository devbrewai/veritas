# PRD: Veritas - KYC/AML Automation & Risk Scoring

## Product Overview

**Product Name:** Veritas  
**Tagline:** "Truth in identity. Trust in compliance."  
**Build Timeline:** 7 days (6 days core + 1 day auth)  
**Purpose:** Automate customer onboarding verification for cross-border payments companies by processing KYC documents, screening against sanctions/adverse media, and assigning risk tiers in minutes instead of days.

**Target Users:** Cross-border payments companies (Series A-C) with manual KYC processes  
**Key Buyers:** Head of Compliance, Risk Operations, Customer Operations  
**Win Metric:** "Reduced KYC review time from 48 hours to 4 seconds, cut cost per onboarding by 65%"

**Predicted Yes Rate:** 60-70% (applies to 79% of target companies)  
**Applicability:** 26/33 prospect companies (B2C remittance + B2B payments)

---

## Problem Statement

Cross-border payments companies spend $50-200 per customer on manual KYC review. Compliance teams manually:

- Extract data from passports, utility bills, business documents (OCR or typing)
- Screen names against OFAC and sanctions lists (copy-paste into databases)
- Search for adverse media mentions (Google search + manual reading)
- Assign risk tiers based on gut feel and checklists (subjective, inconsistent)

**Current State:**

- 24-72 hours per customer onboarding
- $150 average cost per customer (compliance team time)
- Bottlenecks at 100+ applications per day
- Inconsistent risk scoring (varies by reviewer)
- Scales linearly with volume (hire more people = only solution)

**Desired State:**

- 4-10 seconds per customer onboarding (automated)
- $45 average cost per customer (65% reduction)
- Handles 1000+ applications per day
- Consistent risk scoring (ML-based, not gut feel)
- Scales with technology (not headcount)

---

## Solution

Veritas automates the entire KYC pipeline:

1. **Document Extraction** - OCR and parsing of ID documents (passport, driver's license), utility bills, business registration
2. **Sanctions Screening** - Check against OFAC SDN, EU sanctions, UN consolidated lists (reused from Sentinel)
3. **Adverse Media Scanning** - Search news/databases for negative mentions (fraud, money laundering, terrorism)
4. **Risk Scoring** - Assign Low/Medium/High risk tier with explainability using ML model
5. **API & Dashboard** - RESTful API for integration, self-service UI for pilots

**Key Differentiation:**

- All-in-one KYC pipeline (competitors sell point solutions)
- Explainable risk tiers (not black box scores)
- Self-service pilot (prospects test with their own documents)
- Built for cross-border use cases (multi-country documents, language support)

---

## Technical Architecture

### Tech Stack

**Backend:**

- Python 3.11+
- FastAPI for API server
- PostgreSQL for document metadata, extraction results, audit logs
- Redis for caching sanctions lists and session data

**Document Processing:**

- Tesseract OCR for text extraction (free, open-source)
- Alternative: Google Vision API (paid, higher accuracy for poor scans)
- pytesseract for Python integration
- python-doctr for structured document parsing
- Pillow for image preprocessing

**Sanctions Screening (Reuse from Sentinel):**

- OFAC SDN list (JSON download)
- EU Consolidated List
- UN Sanctions List
- Fuzzy matching with rapidfuzz (Levenshtein distance)
- Phonetic matching with metaphone

**Adverse Media:**

- GDELT API for news mentions (free tier: 250 queries/day)
- Alternative: NewsAPI (free tier: 100 requests/day)
- Keyword search: "{full_name}" AND (fraud OR scam OR money laundering OR sanctions OR terrorist)
- Sentiment analysis: TextBlob or VADER (simple, no ML needed)

**Risk Scoring:**

- LightGBM or XGBoost for risk classification
- Features: document quality score, sanctions match confidence, adverse media count/sentiment, country risk, business type risk
- Calibrated probability output (Platt scaling)
- SHAP values for explainability

**Authentication & Multi-Tenancy:**

- Better Auth (email/password, session management)
- Multi-tenant schema: user_id foreign key on all tables
- Row-level security in queries

**Frontend:**

- Next.js 14 (App Router)
- Tailwind CSS
- Shadcn/UI components (form, card, badge, table)
- React Hook Form for document upload
- React Dropzone for drag-and-drop file upload

**Deployment:**

- Backend: Render.com (Python web service)
- Frontend: Vercel
- Database: Neon PostgreSQL (serverless, free tier: 512MB, branching, connection pooling)
- Redis: Render Redis (free tier: 25MB)
- Auth & App share same Neon database (Better Auth manages its own tables)

---

## Data Schema

### Users Table (Better Auth)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

### Documents Table

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) NOT NULL, -- Multi-tenant isolation
    customer_id VARCHAR(255),
    document_type VARCHAR(50), -- passport, utility_bill, business_reg, drivers_license
    uploaded_at TIMESTAMP DEFAULT NOW(),
    file_path VARCHAR(500),
    file_size_bytes INT,
    extracted_data JSONB,
    ocr_confidence FLOAT,
    processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT
);

CREATE INDEX idx_user_documents ON documents(user_id, uploaded_at DESC);
CREATE INDEX idx_customer_documents ON documents(user_id, customer_id);
```

### Screening Results Table

```sql
CREATE TABLE screening_results (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) NOT NULL, -- Multi-tenant isolation
    document_id UUID REFERENCES documents(id),
    customer_id VARCHAR(255),
    full_name VARCHAR(255),
    sanctions_match BOOLEAN,
    sanctions_details JSONB, -- {list: "OFAC", confidence: 0.95, matched_name: "..."}
    adverse_media_count INT,
    adverse_media_summary JSONB, -- [{title: "...", url: "...", sentiment: -0.8}]
    risk_score FLOAT, -- 0-1 probability
    risk_tier VARCHAR(20), -- Low, Medium, High
    risk_reasons JSONB, -- [{feature: "sanctions_match", contribution: 0.4}]
    recommendation VARCHAR(20), -- Approve, Review, Reject
    screened_at TIMESTAMP DEFAULT NOW(),
    processing_time_ms INT
);

CREATE INDEX idx_user_screening ON screening_results(user_id, screened_at DESC);
```

### Sanctions Lists (Redis Cache)

```
Key: sanctions:ofac:{name_hash}
Value: {
  "full_name": "John Doe",
  "aliases": ["J. Doe", "Jonathan Doe"],
  "country": "XX",
  "list_date": "2024-01-15"
}
TTL: 86400 (24 hours, refresh daily)
```

---

## API Specification

### Base URL

```
https://veritas-api.onrender.com/v1
```

### Authentication

All endpoints (except /auth/\*) require Bearer token:

```http
Authorization: Bearer <jwt_token>
```

### Endpoints

#### 1. Register / Login

```http
POST /auth/register
Content-Type: application/json

Request:
{
  "email": "compliance@company.com",
  "password": "SecurePass123!",
  "company_name": "Acme Payments"
}

Response (201 Created):
{
  "user_id": "user_abc123",
  "email": "compliance@company.com",
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

```http
POST /auth/login
Content-Type: application/json

Request:
{
  "email": "compliance@company.com",
  "password": "SecurePass123!"
}

Response (200 OK):
{
  "user_id": "user_abc123",
  "email": "compliance@company.com",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "company_name": "Acme Payments"
}
```

#### 2. Upload Document

```http
POST /documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

Request:
{
  "customer_id": "cust_123",
  "document_type": "passport",
  "file": <binary data>
}

Response (202 Accepted):
{
  "document_id": "doc_abc123",
  "status": "processing",
  "estimated_completion_seconds": 8
}
```

#### 3. Get KYC Results

```http
GET /kyc/{customer_id}
Authorization: Bearer <token>

Response (200 OK):
{
  "customer_id": "cust_123",
  "documents": [
    {
      "document_id": "doc_abc123",
      "type": "passport",
      "uploaded_at": "2026-01-15T10:30:00Z",
      "extracted_data": {
        "full_name": "John Smith",
        "date_of_birth": "1985-03-15",
        "nationality": "US",
        "passport_number": "123456789",
        "issue_date": "2020-03-15",
        "expiry_date": "2030-03-15",
        "issuing_country": "USA"
      },
      "ocr_confidence": 0.96
    },
    {
      "document_id": "doc_xyz456",
      "type": "utility_bill",
      "extracted_data": {
        "name": "John Smith",
        "address": "123 Main St, New York, NY 10001",
        "bill_date": "2025-12-15",
        "utility_provider": "Con Edison"
      },
      "ocr_confidence": 0.89
    }
  ],
  "screening": {
    "sanctions_match": false,
    "sanctions_checked": ["OFAC", "EU", "UN"],
    "adverse_media": {
      "mentions_found": 0,
      "searches_performed": ["GDELT", "NewsAPI"],
      "summary": "No negative mentions found in news databases"
    }
  },
  "risk_assessment": {
    "score": 0.15,
    "tier": "Low",
    "reasons": [
      {
        "factor": "Clean sanctions screening",
        "contribution": -0.25
      },
      {
        "factor": "No adverse media",
        "contribution": -0.15
      },
      {
        "factor": "Low-risk country (US)",
        "contribution": -0.10
      },
      {
        "factor": "High document quality (96% confidence)",
        "contribution": -0.05
      }
    ],
    "recommendation": "Approve"
  },
  "processed_at": "2026-01-15T10:30:08Z",
  "total_processing_time_ms": 4230
}
```

#### 4. Batch KYC Processing

```http
POST /kyc/batch
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "customers": [
    {
      "customer_id": "cust_123",
      "documents": [
        {"type": "passport", "file_url": "s3://..."},
        {"type": "utility_bill", "file_url": "s3://..."}
      ]
    },
    // ... more customers
  ]
}

Response (202 Accepted):
{
  "batch_id": "batch_xyz",
  "total_customers": 50,
  "status": "processing",
  "estimated_completion_minutes": 3
}
```

#### 5. Get User Statistics

```http
GET /users/me/stats
Authorization: Bearer <token>

Response (200 OK):
{
  "total_documents_processed": 127,
  "customers_screened": 89,
  "average_processing_time_seconds": 5.2,
  "risk_distribution": {
    "Low": 76,
    "Medium": 11,
    "High": 2
  },
  "cost_savings_vs_manual": {
    "time_saved_hours": 104,
    "estimated_cost_savings_usd": 9180
  }
}
```

---

## Features & Implementation Timeline

### Day 1: Project Setup & Document Extraction

**Tasks:**

- [x] Initialize monorepo structure (apps/api, apps/web, packages/shared)
- [x] Set up FastAPI backend with PostgreSQL
- [x] Implement Tesseract OCR pipeline
- [x] Build passport parser:
  - Extract: full_name, date_of_birth, passport_number, nationality, issue_date, expiry_date
  - Handle common passport formats (MRZ - Machine Readable Zone)
- [x] Store extracted data in documents table
- [x] Test with sample passport images

**Deliverables:**

- Working OCR pipeline
- Passport data extraction with >90% accuracy on clear scans

### Day 2: More Document Types + Data Models

**Tasks:**

- [x] Add utility bill parser:
  - Extract: name, address, bill_date, utility_provider
  - Handle PDF and image formats
- [x] Add business document parser:
  - Extract: company_name, registration_number, directors, registration_date
- [x] Implement image preprocessing (deskew, denoise, contrast enhancement)
- [x] Add OCR confidence scoring
- [x] Handle errors gracefully (poor quality scans, unsupported formats)

**Deliverables:**

- [x] Multi-document type support
- [x] Robust error handling

### Day 3: Sanctions Screening (Reuse Sentinel)

**Tasks:**

- [x] **Copy sanctions screening engine from Sentinel**
  - Adapted `text_utils.py` - Text normalization and tokenization
  - Adapted `matcher.py` - Fuzzy matching engine with blocking indices
- [x] Adapt for full name + alias matching (not just transaction screening)
- [x] Add country-based filtering (match passport nationality)
- [ ] Redis caching for sanctions lists (deferred to future iteration)
- [x] Test fuzzy matching with sample names
- [x] Return top match with confidence score (0-1)

**Deliverables:**

- [x] Sanctions screening integrated (reusing Sentinel code)
- [x] <2 second screening time (actual: <50ms)

### Day 4: Adverse Media + Risk Model Training

**Tasks:**

- [x] GDELT API integration:
  - Search query: "{full_name}" AND (fraud OR scam OR "money laundering" OR sanctions)
  - Parse results, extract article titles, URLs, dates
  - Implemented async httpx client with rate limiting and error handling
- [x] Sentiment analysis on article titles (VADER)
  - Created `SentimentAnalyzer` wrapper with batch processing
  - Categories: Negative (<-0.05), Neutral, Positive (>0.05)
- [x] Count negative mentions, compute average sentiment
  - `AdverseMediaService` orchestrates GDELT + sentiment analysis
  - Updates `ScreeningResult` with adverse media findings
- [x] Create synthetic training data for risk model:
  - 1000 samples with labels (Low/Medium/High risk)
  - Features: document_quality, sanctions_score, sanctions_match, adverse_media_count, adverse_media_sentiment, country_risk, document_age_days
  - Realistic distributions based on KYC domain knowledge
- [x] Train LightGBM classifier
  - Multi-class classification (Low/Medium/High)
  - 3-fold cross-validation for calibration
  - 98% accuracy on test set
- [x] Calibrate probabilities (Platt scaling via CalibratedClassifierCV)
- [x] Define risk tiers: Low (<0.3), Medium (0.3-0.7), High (>0.7)
  - Recommendations: Approve, Review, Reject
- [x] Generate SHAP explanations (top 5 contributing features)
  - TreeExplainer for multi-class LightGBM
  - Human-readable risk factor formatting
- [x] API endpoints for risk scoring:
  - `POST /risk/adverse-media` - Scan name
  - `POST /risk/adverse-media/document/{id}` - Scan from document
  - `POST /risk/score` - Score from features
  - `POST /risk/score/screening/{id}` - Score existing screening
  - `GET /risk/health` - Service status

**Deliverables:**

- [x] Adverse media scanning working
- [x] Risk model trained and calibrated (98% accuracy)
- [x] Explainable risk tiers with SHAP contributions

### Day 5: Better Auth + Multi-Tenancy

**Tasks:**

- [x] Install Better Auth (`bun add better-auth`)
- [x] Configure Better Auth with JWT plugin and PostgreSQL:
  - Server config at `apps/web/src/lib/auth.ts`
  - Client config at `apps/web/src/lib/auth-client.ts`
  - JWT plugin with EdDSA/Ed25519 algorithm
  - JWKS endpoint at `/api/auth/jwks`
- [x] Create users table (Better Auth auto-creates: user, account, session, verification, jwks)
- [x] Implement registration endpoint (`/api/auth/sign-up/email`)
- [x] Implement login endpoint (`/api/auth/sign-in/email`)
- [x] Add JWT validation in FastAPI:
  - JWKS fetcher service (`src/services/auth/jwks.py`)
  - Token validation service (`src/services/auth/tokens.py`)
  - Auth dependency (`src/dependencies/auth.py`)
  - Validates JWT via JWKS without calling Better Auth
- [x] Add `user_id` column to Document and ScreeningResult models
- [x] Update all queries to filter by user_id:
  - Document endpoints (upload, get)
  - Screening endpoints (document screening)
  - Risk endpoints (adverse media, risk scoring)
- [x] Test multi-tenant data isolation (9 tests in `test_multi_tenancy.py`)

**Architecture:**
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Next.js App   │────▶│   Better Auth    │────▶│  FastAPI API    │
│   (Frontend)    │     │   (JWT + JWKS)   │     │ (Validates JWT) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Deliverables:**

- [x] Working auth system (Better Auth in Next.js)
- [x] Multi-tenant data isolation (user_id filtering)
- [x] Protected API endpoints (JWT Bearer tokens)
- [x] 326 tests passing (including 9 isolation tests)

### Day 6: API Endpoints + Background Processing

**Tasks:**

- [ ] Document upload endpoint (/documents/upload)
  - Store file in local storage or S3
  - Create database record
  - Trigger async processing
- [ ] KYC results endpoint (/kyc/{customer_id})
  - Aggregate document extraction + screening + risk assessment
  - Return unified response
- [ ] Batch processing endpoint (/kyc/batch)
  - Accept multiple customers
  - Process in background queue (Python asyncio or Celery)
- [ ] User stats endpoint (/users/me/stats)
- [ ] Error handling and validation (Pydantic models)
- [ ] Rate limiting (10 uploads/min per user for demo)
- [ ] API documentation (auto-generated Swagger UI)

**Deliverables:**

- Complete API with all endpoints
- Async processing for scalability
- API docs at /docs

### Day 7: Demo UI

**Tasks:**

- [ ] Next.js setup with Tailwind CSS
- [ ] Login/Register pages (Better Auth client)
- [ ] Protected dashboard route
- [ ] Document upload form:
  - Drag-and-drop file upload (React Dropzone)
  - Customer ID input
  - Document type selector
  - Submit button
- [ ] Processing status display:
  - Progress bar or spinner
  - Real-time status updates (polling or WebSocket)
- [ ] Results dashboard:
  - Extracted data card (passport details, utility bill info)
  - Sanctions screening status (green checkmark or red warning)
  - Adverse media summary (count, sample headlines)
  - Risk tier badge (color-coded: green/yellow/red)
  - Risk reasons (top 5 factors with contribution bars)
  - Recommendation (Approve/Review/Reject)
- [ ] Comparison table:
  - Manual process: 48 hours, $150 per customer
  - Veritas: 4 seconds, $45 per customer
  - Savings calculator (based on volume)
- [ ] Batch results view (table of processed customers)
- [ ] Responsive design (mobile-friendly)

**Deliverables:**

- Self-service demo UI
- Professional appearance
- Mobile responsive

---

## Acceptance Criteria

### Functional Requirements

- [ ] Process passport in <10 seconds (p95)
- [ ] OCR accuracy >85% on clear documents (90%+ target)
- [ ] Sanctions screening returns results in <3 seconds
- [ ] Adverse media search completes in <5 seconds
- [ ] End-to-end KYC processing in <15 seconds total
- [ ] Risk tier accuracy >80% on validation set (synthetic data)
- [x] Multi-tenant isolation verified (users can't see each other's data) - 9 tests in `test_multi_tenancy.py`
- [x] Auth system working (register, login, protected routes) - Better Auth + JWT validation

### Non-Functional Requirements

- [ ] Support 50 concurrent document uploads (free tier limit)
- [ ] Handle PDF, JPG, PNG, HEIC formats
- [ ] Graceful error handling for poor quality scans (request re-upload)
- [ ] Audit log for all screening decisions (compliance requirement)
- [ ] GDPR-compliant data handling:
  - Document retention policy (30 days, then delete)
  - Data export on request
  - Right to be forgotten
- [ ] API uptime >99% during demo period

### Security Requirements

- [x] Passwords hashed (bcrypt, handled by Better Auth)
- [x] JWT tokens with expiration (7 days, EdDSA/Ed25519 signed)
- [x] Row-level security (all queries filter by user_id)
- [ ] File upload validation (max 10MB, allowed types only)
- [ ] Rate limiting (prevent abuse)
- [ ] HTTPS only (enforced by Render + Vercel)

---

## Demo Script (3 Minutes)

### Minute 1: The Problem (0:00-1:00)

**Narration:**
"Cross-border payments companies spend $50 to $200 per customer on manual KYC review. Compliance teams manually extract data from passports, screen sanctions lists, and search for adverse media. This takes 24 to 72 hours per customer and creates massive bottlenecks."

**Visuals:**

- Screenshot of manual KYC checklist (spreadsheet)
- Timeline graphic: Application → Manual Review → 48 hours → Approval
- Cost breakdown: 2 hours @ $75/hr = $150 per customer

### Minute 2: The Solution (1:00-2:30)

**Narration:**
"Veritas automates the entire KYC pipeline. Watch as I upload a passport and utility bill."

**Visuals:**

- Log into Veritas dashboard
- Drag-and-drop passport image
- Click "Process Document"
- Real-time processing indicator (3-4 seconds)
- Results appear:
  - Extracted data: John Smith, DOB 1985-03-15, Passport #123456789
  - OCR confidence: 96%
  - Sanctions: No match (OFAC, EU, UN all clear)
  - Adverse media: 0 negative mentions
  - Risk tier: Low (score 0.15)
  - Recommendation: Approve

**Narration (cont):**
"The system extracted passport data in 2 seconds, screened sanctions lists in 1 second, checked adverse media in 1 second, and assigned a risk tier in under 4 seconds total. The ML model explains exactly why this customer is low risk."

**Visuals:**

- Risk reasons panel showing feature contributions
- Sanctions check green checkmark
- Total processing time: 4.2 seconds

### Minute 3: The Results (2:30-3:00)

**Narration:**
"Veritas reduces KYC time from 48 hours to 4 seconds—that's 95% faster. Cost drops from $150 to $45 per customer—65% cheaper. And every customer gets consistent risk scoring, not gut feel."

**Visuals:**

- Comparison table:
  - Manual: 48 hrs, $150, inconsistent
  - Veritas: 4 sec, $45, ML-based consistency
- Savings calculator: "Process 100 customers/month → Save $10,500"
- Client testimonial (preview): "Cut our onboarding time by 90%..."

**CTA:** "Ready to test Veritas with your KYC documents? I'll set up a private account for you today."

**Button:** "Book a 15-Minute Demo"

---

## One-Pager Content

### Veritas: Automate KYC in Seconds, Not Days

**The Problem:**
Cross-border payments companies spend $50-200 per customer on manual KYC review, taking 24-72 hours per onboarding. Compliance teams manually extract data, screen sanctions, and search adverse media.

**The Solution:**
Veritas automates document extraction, sanctions screening, adverse media scanning, and risk scoring in under 10 seconds.

**The Tech:**

- OCR + parsing for passports, IDs, utility bills, business documents
- Sanctions screening against OFAC, EU, UN lists (reused from Sentinel)
- Adverse media detection via GDELT and NewsAPI
- ML-based risk scoring with explainability (LightGBM + SHAP)
- Self-service pilot UI with Better Auth

**The Results:**

- 95% faster: 48 hours → 4 seconds
- 65% cheaper: $150 → $45 per customer
- 100% coverage: Every customer screened, zero manual reviews
- Consistent: ML-based risk scoring, not gut feel

**The Stack:**

- Python, FastAPI, PostgreSQL, Redis
- Tesseract OCR, LightGBM, Better Auth
- Deployed on Render + Vercel

**Pilot Offer:**
Log in and upload 10-20 of your recent KYC applications. Process them through Veritas for 2-3 weeks. If we cut your review time by 50%+, give us a testimonial.

[Live Demo] [GitHub] [Book a Call]

---

## Success Metrics for Pilots

### Track During Pilot (2-3 weeks)

- Documents processed (target: 20-50 per pilot)
- Average processing time (target: <10 seconds)
- OCR accuracy rate (target: >85%)
- Sanctions false positive rate (target: <5%)
- User satisfaction (1-10 score, target: 8+)
- Time saved vs manual process (hours)
- Cost saved vs manual process (dollars)

### Target for Testimonial

- **Time reduction:** >50% (48 hrs → <24 hrs minimum, ideally <1 hr)
- **Cost reduction:** >60% ($150 → <$60 per customer)
- **Accuracy:** <5% false positive rate on sanctions screening
- **Satisfaction:** 8+/10 from compliance team

### Example Testimonial

```
"Our compliance team was drowning in manual KYC reviews—every customer
took 48 hours to onboard, costing us $150 in team time.

We piloted Veritas and immediately saw our review time drop to under
10 seconds per customer. The document extraction was 95% accurate,
and the risk scoring gave us confidence to approve low-risk customers
automatically.

This freed up 30 hours per week for our compliance team and cut our
cost per customer by 70%. We're now onboarding 10x more customers
with the same team size."

— Maria Rodriguez, Head of Compliance at [Company]
```

---

## Deployment Checklist

### Backend (Render)

- [ ] Create Render account (render.com)
- [ ] Connect GitHub repo (veritas-api)
- [ ] Create Web Service:
  - Name: veritas-api
  - Environment: Python 3.11
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - Instance type: Free (512MB RAM, 0.1 CPU)
- [ ] Create PostgreSQL database:
  - Name: veritas-db
  - Plan: Free (1GB storage)
- [ ] Create Redis instance:
  - Name: veritas-redis
  - Plan: Free (25MB)
- [ ] Set environment variables:
  ```
  DATABASE_URL=postgresql://...
  REDIS_URL=redis://...
  JWT_SECRET=<random_string>
  OFAC_LIST_URL=https://...
  GDELT_API_KEY=<optional>
  NEWSAPI_KEY=<optional>
  ```
- [ ] Deploy and test /health endpoint

### Frontend (Vercel)

- [ ] Create Vercel account (vercel.com)
- [ ] Connect GitHub repo (veritas-ui)
- [ ] Configure project:
  - Framework: Next.js
  - Root directory: apps/web
  - Build command: `npm run build`
  - Output directory: .next
- [ ] Set environment variables:
  ```
  NEXT_PUBLIC_API_URL=https://veritas-api.onrender.com
  NEXT_PUBLIC_BETTER_AUTH_URL=https://veritas-api.onrender.com/auth
  ```
- [ ] Deploy and verify build
- [ ] Add custom domain: veritas.devbrew.ai

### Monitoring

- [ ] UptimeRobot (free tier):
  - Monitor /health endpoint
  - Ping every 5 minutes (keeps Render warm)
  - Alert on downtime
- [ ] Sentry (free tier):
  - Error tracking for backend
  - Frontend error tracking
- [ ] Analytics:
  - Vercel Analytics (built-in)
  - Simple dashboard: signups, documents processed, errors

---

## Reusable Components (For Future Projects)

### From Sentinel to Veritas (Already Reused)

- ✅ Sanctions screening engine
- ✅ Redis caching patterns
- ✅ API error handling
- ✅ FastAPI project structure

### From Veritas to Meridian (To Be Reused)

- ✅ Better Auth setup and configuration (JWT plugin, JWKS)
- ✅ Multi-tenant data schema patterns (user_id on all tables)
- ✅ Protected route middleware (FastAPI JWT validation via JWKS)
- User registration/login UI components (basic forms created)
- Dashboard layout components (to be built in Day 7)

---

## Risk Mitigation

| Risk                                         | Impact   | Mitigation                                                                             |
| -------------------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| OCR fails on poor quality scans              | High     | Image preprocessing, quality check, request re-upload with instructions                |
| Sanctions lists out of date                  | Medium   | Daily automated refresh, version control lists, alert on stale data                    |
| Adverse media API rate limits hit            | Medium   | Cache results (7 days), use multiple sources (GDELT + NewsAPI), batch requests         |
| False positives on common names (John Smith) | High     | Add middle name + DOB matching, country filters, manual review workflow for edge cases |
| Multi-tenant data leak                       | Critical | Comprehensive testing, automated checks in CI/CD, row-level security validation        |
| Auth system vulnerability                    | Critical | Use Better Auth (battle-tested), regular security audits, HTTPS only                   |

---

## Tech Debt & Future Enhancements

### Known Limitations (Document for Pilots)

- OCR optimized for English documents (limited multi-language support)
- Adverse media search is English-only
- Risk model trained on synthetic data (not real customer patterns)
- Document retention: 30 days (compliance requirement, then auto-delete)
- Free tier limits: 100 documents/month per pilot (Render + API limits)

### Future Enhancements (Post-Testimonials)

- Multi-language OCR (support Spanish, French, Arabic documents)
- Enhanced adverse media: Bloomberg, LexisNexis integration (paid sources)
- Custom risk models per client (trained on their specific risk patterns)
- Real-time document verification (check passport against government APIs)
- Automated workflow actions (send to manual review queue, trigger 3rd party checks)
- Bulk upload (CSV of customer IDs → automated document retrieval and processing)

---

## Outreach Strategy (Veritas-Specific)

### Target Companies (26 Best Fits)

**B2C Remittance (High Priority):**

- NALA, Chipper Cash, LemFi, Sendwave, Remitly, Afriex, Felix Pago, Taptap Send
- Pain: High KYC volume (1000s of customers/month), manual bottleneck
- Pitch: "Cut your onboarding time from 48 hrs to 4 seconds, handle 10x volume with same team"

**B2B Payments:**

- Papaya Global, Jeeves, Airwallex, Nium, Tazapay, Aspire
- Pain: B2B onboarding friction (business documents, complex verification)
- Pitch: "Automate business document extraction, speed up merchant onboarding by 90%"

**Infrastructure/API:**

- Routefusion, Palla, Grey, Grain (if they onboard customers directly)
- Pain: Compliance overhead for platform customers
- Pitch: "Offer embedded KYC to your customers, white-label our API"

### Email Template

```
Subject: [Company] - KYC automation pilot offer

Hey [Name],

Saw [Company] just [recent news/funding/expansion]. Congrats.

At [estimated volume] customers per month, your compliance team is
probably doing 100+ hours of manual KYC reviews. That's a $15K+/month
bottleneck.

I built Veritas, a KYC automation system for cross-border payments.
Here's a 3-min demo: [link to veritas.devbrew.ai]

For [Company] specifically:
- Process [passport/business docs] for [their markets]
- Sanctions screening across [jurisdictions]
- Risk scoring that cuts review time from 48 hrs to <10 seconds

The pilot: I'll set up a private account. Upload 10-20 recent applications,
see the side-by-side comparison. If we cut your time by 50%+, you give
us a testimonial.

Quick call this week to get you set up?

Best,
Joe

P.S. Here's the login: [custom link with temp password]
```

### Follow-Up Sequence

**Day 3:** "Hey [Name], did you get a chance to try Veritas? Any questions?"  
**Day 7:** "Sharing a case study on KYC automation ROI: [link]. Thought you'd find it relevant."  
**Day 14:** "Last ping - still interested in cutting your KYC time by 90%? I have 2 pilot slots left this month."

---

## Timeline to Ship (7 Days)

**Day 1:** Project setup + passport extraction  
**Day 2:** Utility bill + business document extraction  
**Day 3:** Sanctions screening (reuse Sentinel)  
**Day 4:** Adverse media + risk model  
**Day 5:** Better Auth + multi-tenancy  
**Day 6:** API endpoints + async processing  
**Day 7:** Demo UI + polish

**Post-Build (Same Day):**

- Deploy to Render + Vercel (2 hours)
- Record demo video (1.5 hours)
- Write one-pager (1 hour)
- Publish case study page (30 min)

**Total:** 7 days build + 5 hours post-production

**Ship Date:** January 17, 2026 (if starting January 10)

---

## The Bottom Line

**Veritas solves a universal pain point:**

- 100% of cross-border companies need KYC
- Current process is manual, expensive, slow
- Clear ROI: 95% faster, 65% cheaper

**Why Veritas converts at 60-70%:**

- Self-service pilot (low friction)
- "Log in and test with your own documents" (tangible proof)
- Regulatory requirement (must-have, not nice-to-have)
- Standalone system (doesn't require ripping out infrastructure)

**First outreach:** Week 3 (January 13-17)  
**First pilot:** Week 4 (January 20-24)  
**First testimonial:** Week 8 (February 17-21)

Build Veritas in Week 2. Start getting testimonials by Week 8.

**That's the move.**
