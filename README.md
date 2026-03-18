# The Autonomous HR

**WhatsApp-native, voice-first, policy-governed HR for the deskless workforce.**  
$0.13 / employee / month. No app. No portal. No HR department required.

---

![Architecture Diagram](arch-diagram.png)

> **Live site:** [raosiddharthp.github.io/The-Autonomous-HR](https://raosiddharthp.github.io/The-Autonomous-HR)  
> **Companion project:** [The Autonomous Enterprise](https://raosiddharthp.github.io/The-Autonomous-Enterprise)

---

## What This Is

A production-grade portfolio architecture for an autonomous HR system targeting the **2.7 billion deskless workers** globally — the 80% of the world's workforce employed in manufacturing, retail, construction, agriculture, and logistics who have no company email, no corporate device, and have been systematically excluded from enterprise HR software.

The system makes HR decisions (leave approval, balance queries, payroll, grievance logging) via **WhatsApp Business API** and **IVR voice calls**, in **6 languages**, governed by an **HR Policy PDF** that the business owner can update without involving a developer.

**Anchor client:** Rathi Textiles Pvt. Ltd. — Nagpur, Maharashtra. 52 employees. 4 locations. ₹2.8 Cr revenue. 6 languages spoken on the floor.

---

## Portfolio Site Structure

| Page | Title | Description |
|------|-------|-------------|
| [index.html](index.html) | Home | Overview, architecture, workflow, cost model, roadmap |
| [page-02.html](page-02.html) | The Problem | 2.7B workers, why existing HR software fails them |
| [page-03.html](page-03.html) | Cost Methodology | Component-by-component cost breakdown with rebuttals |
| [page-04.html](page-04.html) | Workflow Simulator | Interactive demo — 4 scenarios × 3 languages |
| [page-05.html](page-05.html) | Client Brief | Rathi Textiles profile, personas, use case catalogue |
| [page-06.html](page-06.html) | TOGAF ADM | Enterprise architecture — Phases A through E |
| [page-07.html](page-07.html) | Agent Architecture | LangGraph state machines, HITL, tool manifest |
| [page-08.html](page-08.html) | MLOps | Model decisions, RAG pipeline, drift detection, retraining |
| [page-09.html](page-09.html) | Platform & Infrastructure | GCP reference architecture, Terraform IaC, security |
| [page-10.html](page-10.html) | Architecture Decision Records | 8 ADRs with context, alternatives, consequences, rebuttals |
| [page-11.html](page-11.html) | HR Policy PDF | Downloadable HR policy for Rathi Textiles |
| [page-glossary.html](page-glossary.html) | Glossary | Every technical term — plain English first |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 · Employee touch points                                │
│  WhatsApp (chat + voice note)  │  IVR / Voice call             │
│  Owner dashboard               │  Policy upload (PDF / WA)     │
└─────────────────────┬──────────────────────┬───────────────────┘
                      │                      │
┌─────────────────────▼──────────────────────▼───────────────────┐
│  Layer 2 · Channel ingestion (low / no cost)                    │
│  WhatsApp Business API (Meta)  │  Exotel / Plivo SIP            │
│  Cloud Run · webhook-gateway   │  Whisper large-v3 (STT)       │
│  Cloud Pub/Sub · INBOUND_MSG   │  NLLB-200 (translation)        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│  Layer 3 · AI orchestration core (GCP asia-south1)              │
│  Intent Router (Gemini Flash)  │  Leave Agent (LangGraph)       │
│  Policy Q&A Agent (RAG)        │  Grievance Agent (LangGraph)   │
│  Onboarding Agent              │  HITL Manager                  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│  Layer 4 · Data & policy (serverless · low cost)                │
│  Firestore (employees · leave · audit log)                      │
│  Supabase pgvector (HR Policy PDF embeddings)                   │
│  Cloud Storage (PDFs · audio · model artifacts)                 │
│  Vertex AI (Gemini Flash · text-embedding-004)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| LLM inference | Gemini 1.5 Flash (Vertex AI) | $0.075/1M tokens · lowest cost capable hosted LLM |
| STT | Whisper large-v3 (OSS, Cloud Run GPU) | 83% cheaper than Google STT · better Indic dialect accuracy |
| Translation | NLLB-200 3.3B (OSS, bundled) | Zero marginal cost · 200 languages · code-switch handling |
| Embeddings | text-embedding-004 (Vertex AI) | 768-dim · $0.00 free tier covers SMB policy indexing |
| Vector store | pgvector on Supabase | Free tier 500MB · HNSW index · sub-10ms retrieval |
| Agent framework | LangGraph | HITL as graph edge condition · not prompt instruction |
| Primary DB | Firestore (Native mode) | Serverless · free tier covers SMB · append-only audit log |
| Compute | Cloud Run | Scale-to-zero · GPU T4 spot for Whisper · 99.95% SLA |
| Event bus | Cloud Pub/Sub | Decouples all services · dead-letter · 7-day retention |
| Channels | WhatsApp Business API + Exotel | 98% open rate · ₹0.35/min vs Twilio $0.013/min |
| IaC | Terraform | All resources defined in code · no console deployments |

---

## Cost Model

**~$6.56 / month for 50 employees = $0.13 / employee / month**

| Component | Monthly Cost |
|-----------|-------------|
| Cloud Run (all services) | ~$2.80 |
| Firestore | $0.00 (free tier) |
| Vertex AI (Gemini Flash + embeddings) | ~$0.04 |
| Cloud Pub/Sub | $0.00 (free tier) |
| Cloud Storage | ~$0.03 |
| Whisper GPU (T4 spot, min-instance) | ~$3.20 |
| Supabase pgvector | $0.00 (free tier) |
| WhatsApp Business API | ~$0.49 |
| Exotel IVR | ~$0.00 (minimal voice usage) |
| **Total** | **~$6.56** |

---

## Repo Structure

```
The-Autonomous-HR/
├── index.html                          # Landing page
├── page-02.html                        # The Problem
├── page-03.html                        # Cost Methodology
├── page-04.html                        # Workflow Simulator
├── page-05.html                        # Client Brief
├── page-06.html                        # TOGAF ADM Phases A–E
├── page-07.html                        # Agent Architecture
├── page-08.html                        # MLOps
├── page-09.html                        # Platform & Infrastructure
├── page-10.html                        # Architecture Decision Records
├── page-11.html                        # HR Policy PDF
├── page-glossary.html                  # Glossary
├── arch-diagram.png                    # System architecture diagram
├── README.md                           # This file
├── CHANGELOG.md                        # Project changelog
└── docs/
    └── hr-policy-rathi-textiles.pdf    # Downloadable HR Policy
```

---

## Deploying the Portfolio Site

This site is a static HTML portfolio — no build step required.

### GitHub Pages (current deployment)

1. Push all files to the `main` branch of your GitHub repo
2. Go to **Settings → Pages → Source → Deploy from branch → main / root**
3. Site is live at `https://{username}.github.io/{repo-name}/`

### Local development

```bash
# Clone the repo
git clone https://github.com/raosiddharthp/The-Autonomous-HR.git
cd The-Autonomous-HR

# Serve locally (Python built-in server)
python3 -m http.server 8080

# Open in browser
open http://localhost:8080
```

---

## Deploying the AutoHR System (GCP)

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| `gcloud` CLI | ≥ 450.0.0 | GCP authentication and deployment |
| `terraform` | ≥ 1.7.0 | Infrastructure provisioning |
| `docker` | ≥ 24.0 | Container builds |
| Python | ≥ 3.11 | Application code |

### Step 1 — GCP project setup

```bash
# Create a new GCP project
gcloud projects create autohr-prod --name="AutoHR Production"
gcloud config set project autohr-prod

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  monitoring.googleapis.com \
  storage.googleapis.com
```

### Step 2 — Terraform initialisation

```bash
cd terraform/

# Create GCS bucket for Terraform state
gsutil mb -l asia-south1 gs://autohr-tf-state-{project-id}

# Initialise Terraform
terraform init \
  -backend-config="bucket=autohr-tf-state-{project-id}" \
  -backend-config="prefix=terraform/state"

# Review infrastructure plan
terraform plan -var="project_id=autohr-prod" -var="region=asia-south1"

# Apply infrastructure
terraform apply -var="project_id=autohr-prod" -var="region=asia-south1"
```

### Step 3 — Required secrets

All secrets are managed in GCP Secret Manager. Populate before first deployment:

```bash
# WhatsApp Business API token
echo -n "YOUR_WA_TOKEN" | gcloud secrets create whatsapp-api-token \
  --data-file=- --project=autohr-prod

# Exotel API key
echo -n "YOUR_EXOTEL_KEY" | gcloud secrets create exotel-api-key \
  --data-file=- --project=autohr-prod

# Supabase connection string
echo -n "postgresql://..." | gcloud secrets create supabase-url \
  --data-file=- --project=autohr-prod
```

### Step 4 — Build and deploy containers

```bash
# Build and push all service containers
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=asia-south1,_PROJECT=autohr-prod

# Verify all services are running
gcloud run services list --region=asia-south1
```

### Step 5 — Deploy HR Policy PDF

```bash
# Upload the initial HR policy to Cloud Storage
gsutil cp docs/hr-policy-rathi-textiles.pdf \
  gs://autohr-policy-documents/hr-policy-v1.0.pdf

# Trigger initial RAG indexing
curl -X POST https://rag-indexer-{hash}-uc.a.run.app/index \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{"version": "1.0", "source": "gs://autohr-policy-documents/hr-policy-v1.0.pdf"}'
```

---

## Updating the HR Policy PDF

The HR Policy PDF is the governing document for all leave decisions. To update it:

1. Edit and export the updated policy as a PDF
2. **Option A — WhatsApp upload:** Send the PDF directly to the system WhatsApp number. The system detects it is a policy document and triggers re-indexing automatically.
3. **Option B — Dashboard upload:** Upload via the owner dashboard. Re-indexing completes in under 3 minutes.
4. The owner receives a WhatsApp confirmation: `"Policy updated. [N] clauses indexed. Now live."`

No developer involvement required for policy updates.

---

## Key Numbers

| Metric | Value | Source |
|--------|-------|--------|
| Deskless workers globally | 2.7 billion | Emergence Capital |
| % of global workforce | 80% | Emergence Capital |
| % with no company email | 83% | InFeedo 2025 |
| Enterprise software spend going to deskless | 1% | Emergence Capital |
| WhatsApp users globally | 3 billion+ | Meta Q4 2024 |
| WhatsApp users in India | 535 million | Quantumrun 2024 |
| WhatsApp message open rate | 98% | Infobip |
| Manufacturing turnover (2024) | 26.3% | Crown Staffing |
| Cost to replace one worker | $10K–$40K | Deloitte via Achievers |
| System total monthly cost (50 emp) | ~$6.56 | See page-03 |
| Cost per employee per month | ~$0.13 | See page-03 |
| Whisper vs Google STT cost reduction | 83% | See page-08 |

---

## About

Built by **Siddharth Rao** — TOGAF Enterprise Architect, GCP Cloud Architect, MLE, SAFe SA/SPC.

This portfolio demonstrates production-grade architecture thinking applied to an underserved market — not just technical depth, but grounding every decision in a real business context, a real cost model, and a real client who has tried and failed with existing solutions.

**GitHub:** [raosiddharthp](https://github.com/raosiddharthp)  
**Companion:** [The Autonomous Enterprise](https://raosiddharthp.github.io/The-Autonomous-Enterprise)

---

*"The deskless workforce runs the world's factories, builds its cities, stocks its shelves, and drives its trucks. They deserve better than a paper register and a phone call to the owner."*
