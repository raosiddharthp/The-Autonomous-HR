# Changelog

All notable changes to The Autonomous HR portfolio are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions represent portfolio build milestones, not software releases.

---

## [1.4.0] — 2026-03-18

### Added — Diagrams across agent, MLOps, and infrastructure pages
- **page-07** — Agent topology map SVG: Worker → Intent Router → Pub/Sub → specialist agents → HITL Manager → Owner → confirmation. Colour-coded by flow type (dispatch, HITL escalation, notification).
- **page-07** — Leave Agent state machine SVG: all 7 states (IDLE, FETCHING, RAG_LOOKUP, EVALUATING, APPROVED, DENIED, HITL_PENDING) with guard conditions on every transition, confidence threshold arrows, timeout path, and audit log annotation.
- **page-07** — HITL decision tree SVG: 4 trigger conditions → HITL Manager → Owner (WA brief) → APPROVE/DENY paths + 4h re-escalation and 24h auto-deny timeout flow.
- **page-08** — RAG pipeline horizontal flow SVG: 5 steps (INGEST → EXTRACT → CHUNK → EMBED → PROMOTE) with per-step timing and total <3 min callout.
- **page-08** — Drift detection matrix SVG: 4-column signal → detect → respond grid (STT acoustic, RAG policy, LLM version, embedding model).
- **page-09** — CI/CD pipeline horizontal flow SVG: 7 stages from feature branch to production, manual gate highlighted, rollback arrow looping back on error rate spike.
- **page-09** — Security trust layers SVG: 4 horizontal bands (Identity, IAM, Transport, Data Integrity) with enforcement point annotations.
- **index.html** — Architecture diagram image (arch-diagram.png) integrated into architecture section with labelled header bar.
- **page-06** — Architecture diagram image integrated into TOGAF Phase D technology architecture section.

### Changed
- **page-07** — Topology section: diagram inserted before agent cards, not replacing them.
- **page-09** — Security section: trust layer diagram inserted before security control cards.

---

## [1.3.0] — 2026-03-17

### Added — pages 08, 09, 10

#### page-08 — MLOps
- Model inventory strip (4 models: Whisper, NLLB-200, Gemini Flash, text-embedding-004) with version, host, and managed/OSS badge.
- 5 decision accordions (D1–D5): Whisper over Google STT, NLLB-200 over Google Translate, Gemini Flash retained, RAG over fine-tuning, Cloud Run jobs over Vertex AI Pipelines. Each accordion: decision, alternative, 2 rebuttals.
- RAG indexing pipeline: 5-step horizontal layout with per-step SLA timing.
- Monitoring dashboard: 6 signal cards (STT latency P95, confidence distribution, RAG retrieval P@1, HITL queue depth, E2E latency, monthly spend). HITL queue depth marked as the one signal surfaced to Priya directly.
- Drift detection: 4 drift types (acoustic, policy, LLM version, embedding) with detection mechanism and automated response.
- Whisper LoRA fine-tuning code snippet (Python, Cloud Run GPU).
- Model registry schema (Firestore) and 3-stage canary deployment strategy.

#### page-09 — Platform & Infrastructure
- GCP reference architecture diagram: dark-background service map with 5 layers, colour-coded by service type.
- Service catalogue: 12 service cards with exact configuration parameters (min/max instances, CPU/memory, ingress, GPU spec, migration triggers).
- Terraform IaC: 6 HCL code blocks (Cloud Run Leave Agent, Firestore security rules, IAM service account bindings, Cloud Run STT GPU, Pub/Sub topics/subscriptions, Cloud Monitoring alerts + billing budget).
- Security model: 6 control cards mapped to SMB threat model.
- CI/CD pipeline: 7-step table with tool at each step.
- IAM service account matrix: 8 service accounts × 6 resource types.

#### page-10 — Architecture Decision Records
- 8 full ADRs: ADR-001 (WhatsApp+IVR), ADR-002 (Firestore), ADR-003 (LangGraph), ADR-004 (Pub/Sub), ADR-005 (Cloud Run), ADR-006 (Exotel), ADR-007 (HITL 24h timeout), ADR-008 (mobile number identity).
- Each ADR: navigable index, context paragraph, decision column, alternatives column, 3-column consequences (positive/negative/mitigation), 2 rebuttals per ADR in dark panel.
- ADR index strip at hero level with scroll-to anchors.

---

## [1.2.0] — 2026-03-14

### Added — pages 05, 06, 07

#### page-05 — Client Brief: Rathi Textiles Pvt. Ltd.
- Business profile: Nagpur, Maharashtra. 52 employees. ₹2.8 Cr revenue. 4 locations.
- 4 quantified pain cards (Keka failure, payroll errors, grievance costs, absenteeism).
- Owner profile: Priya Rathi, 34, MBA Pune.
- 3 employee personas with language, role, and friction points.
- Stakeholder register with power/interest ratings.
- AI readiness audit (4 dimensions, animated score bars).
- 14-item use case catalogue across 5 phases.

#### page-06 — TOGAF ADM Phases A–E
- Phase A: architecture vision statement, 6 architecture principles with rationale.
- Phase B: business capability map, 5-step business process, KPI table.
- Phase C: 5-layer application architecture, 6-entity data architecture, data governance rules.
- Phase D: technology architecture with 9 tech cards (Gemini Flash, Firestore, Cloud Run, Pub/Sub, Whisper, NLLB-200, pgvector, Exotel, LangGraph) each with justification and rejected alternative.
- Phase E: 6-step migration sequence from Phase 0 (WhatsApp gateway) to Phase 5 (analytics).
- Sticky progress strip with scroll-spy across all 5 phases.

#### page-07 — Agent Architecture
- 6 agent cards (Intent Router, Leave Agent, Payroll Agent, Onboarding Agent, Grievance Agent, Policy Q&A Agent) with autonomy boundary and tool tags.
- Leave Agent state machine: 7 states, all transitions, guard conditions, confidence threshold logic.
- Tool manifest table: 8 tools across Leave Agent, each with input/output schema and failure behaviour.
- HITL specification: 4 trigger conditions, presentation contract, decision interface, timeout policy.
- 6 infrastructure guardrails (append-only audit, IAM boundary, max consecutive days, probation flag, HITL threshold, no balance invention).
- HR Policy PDF CTA section.

---

## [1.1.0] — 2026-03-10

### Added — pages 02, 03, 04

#### page-02 — The Problem in Depth
- 8 stat cards: 2.7B workers, 1% software funding, 83% no email, 98% WA open rate, 26.3% turnover, $40K replacement cost, 6 languages at Rathi Textiles, 1 HR tool for 52 employees.
- Workforce breakdown by industry.
- 6 pain point narratives (the paper register, the missed payslip, the impossible grievance, the language barrier, the proximity tax, the trust deficit).
- Turnover cost comparison table.
- Channel comparison matrix: SMS vs email vs app vs WhatsApp vs IVR.
- 12 cited primary sources.

#### page-03 — Cost Methodology
- 6 component accordions (C1 Cloud Run, C2 Firestore, C3 Vertex AI, C4 STT, C5 WhatsApp, C6 Exotel) with per-component calculation, rationale, and rebuttal.
- Sensitivity analysis table: 15, 50, 200 employees.
- Market comparator table (Keka, Darwinbox, BambooHR, Rippling vs $0.13).
- Methodology notes on Exotel pricing opacity and WhatsApp July 2025 pricing change.

#### page-04 — Interactive Workflow Simulator
- Split-screen layout: WhatsApp phone mockup (left) + system internals terminal (right).
- 4 scenarios: Leave Approved, Leave Denied, HITL Escalation, Policy Query.
- 3 languages per scenario: Hindi, Telugu, Marathi.
- 12 fully scripted conversation + terminal combinations.
- HITL scenario: owner phone mockup with tap-to-approve/deny UI.
- SLA timers per step.

---

## [1.0.0] — 2026-03-07

### Added — Foundation

#### index.html — Landing page
- 6-section layout: Why Now, Philosophy, Architecture, Workflow, Cost Model, Roadmap.
- Architecture layer breakdown (4 layers: channels, ingestion, AI core, data).
- Cost model preview ($0.13/employee/month callout).
- Phase roadmap (Phase 0 to Phase 5).
- Scroll-reveal animations throughout.
- Paper texture, saffron accent, Fraunces + Instrument Serif + DM Mono typography system.

#### Design system established
- Colour palette: --ink (#1a1612), --paper (#f5f0e8), --saffron (#c4620a), --paper-2, --paper-3, --rule.
- Typography: Instrument Serif (display), Fraunces (serif body), DM Mono (monospace UI).
- Paper noise texture via SVG filter.
- Reveal animation system via IntersectionObserver.
- Deliberate contrast with The Autonomous Enterprise dark palette — field manual vs European tech aesthetic.

#### Architecture decisions (pre-ADR)
- GCP as backbone with OSS at inference edges.
- WhatsApp + IVR as sole employee channels (no app, no portal).
- Firestore as primary database (serverless, free tier covers SMB).
- Cloud Run as sole compute platform (no GKE).
- LangGraph for agent orchestration (HITL as graph edge, not prompt).
- Exotel over Twilio for India voice (68% cost reduction).
- Whisper large-v3 over Google STT (83% cost reduction, better Indic accuracy).
- pgvector on Supabase for RAG (free tier, sub-10ms retrieval).

---

## Planned

### [1.5.0] — Upcoming
- page-11 (HR Policy PDF landing page) with download, section map, and RAG-in-action examples.
- page-glossary (complete A–Z technical glossary).
- Navigation audit: ensure all pages link to each other in nav and footer.
- README and CHANGELOG committed to repo.

### [2.0.0] — Future
- Interactive cost calculator (React artifact).
- Working demo environment on GCP Cloud Run (auto-destroys after 30 minutes).
- Payroll agent architecture page.
- Onboarding agent flow diagram.
- Real WhatsApp sandbox demo link.
