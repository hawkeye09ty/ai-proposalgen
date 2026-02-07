# ProposalAI - Product Requirements Document

## Original Problem Statement
Build a "ProposalAI" application - a proposal builder app using OpenAI GPT-5.2 with Emergent LLM key that:
- Takes inputs like client names, project details, and clauses
- Includes a dashboard to show proposal status (Draft, Pending Review, Sent, Accepted, Rejected)
- Features file upload for requirement documents
- Supports PDF export and proposal templates
- Has an analytics dashboard to track deal metrics
- Integrates email sending via Resend
- Automates proposal creation via Brevo CRM and Google Docs

## Architecture

### Tech Stack
- **Frontend**: React, React Router, Axios, Chart.js, jsPDF, Shadcn/UI
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (via emergentintegrations), Resend, Brevo, Google Docs (pending)

### File Structure
```
/app/
├── backend/
│   ├── .env                 # API keys and config
│   ├── requirements.txt     # Python dependencies
│   ├── server.py           # Monolithic FastAPI app
│   └── tests/              # Pytest test files
└── frontend/
    ├── .env                # REACT_APP_BACKEND_URL
    ├── package.json        # Node dependencies
    └── src/
        ├── App.js          # Routes
        ├── components/
        │   ├── ClauseSelector.js
        │   ├── Layout.js
        │   ├── Sidebar.js  # Navigation with Settings
        │   └── ui/         # Shadcn components
        └── pages/
            ├── Analytics.js
            ├── ClauseLibrary.js
            ├── CreateProposal.js
            ├── Dashboard.js    # With inline editing
            ├── ProposalDetail.js
            └── Settings.js     # NEW - Integration config
```

### Key Database Collections
- **proposals**: {id, client_name, project_description, budget_range, timeline, status, content, deal_value, created_at, updated_at, accepted_at}
- **clauses**: {id, title, content, category, is_custom, created_at}
- **templates**: {id, name, industry, description, prompt_template, created_at}
- **email_logs**: {id, proposal_id, recipient_email, subject, sent_at, opened, opened_at, clicked, clicked_at, resend_email_id}
- **settings**: {company_name, default_sender_email, brevo_polling_enabled, google_doc_template_id, approval_keyword, ...}
- **brevo_deals**: {id, brevo_deal_id, deal_name, company_name, contact_email, deal_value, stage, status, raw_data}

## What's Been Implemented (Dec 2025)

### Core Features ✅
- [x] Full-stack application with React + FastAPI + MongoDB
- [x] Dashboard with proposal stats and filtering by status
- [x] Proposal creation with client info, templates, and file upload
- [x] AI-powered proposal generation using OpenAI GPT-5.2
- [x] Clause Library with predefined and custom clauses
- [x] Proposal templates (Technology, Consulting, Creative)
- [x] PDF export functionality
- [x] Status management (Draft → Pending Review → Sent → Accepted/Rejected)

### Email Integration ✅
- [x] Resend API integration for sending proposals
- [x] Email tracking (opens and clicks)
- [x] Email logs on proposal detail page
- [x] Custom message support in email sending

### Analytics Dashboard ✅
- [x] Acceptance rate calculation
- [x] Average deal size
- [x] Average time to close
- [x] Status distribution chart
- [x] Total revenue tracking

### Settings Page ✅ (NEW)
- [x] Integration status monitoring (Resend, Brevo, Google Docs)
- [x] General settings (company name, sender email)
- [x] Email notification preferences
- [x] Brevo polling configuration
- [x] Google Docs template ID setting
- [x] Approval keyword configuration

### Dashboard Inline Editing ✅ (NEW)
- [x] Edit button on each proposal card
- [x] Inline form for quick field updates
- [x] Editable: client name, budget, timeline, deal value, status
- [x] Save/Cancel functionality

### Brevo CRM Integration ✅ (NEW)
- [x] Integration status check endpoint
- [x] Opportunities fetch endpoint
- [x] Opportunity update endpoint
- [x] Webhook endpoint for stage changes
- [x] Pending deals tracking

## In Progress / Blocked

### Google Docs Integration (BLOCKED)
- Waiting for user to provide service account JSON credentials
- Service account email known: `proposalai@fiery-emblem-485811-a0.iam.gserviceaccount.com`
- **When credentials provided**:
  - Create Google Doc from template
  - Populate with Brevo opportunity data
  - Share for team editing
  - Monitor for "APPROVED" comments
  - Generate PDF and attach to Brevo on approval

## Prioritized Backlog

### P0 (Critical)
- [ ] Google Docs integration (waiting for credentials)
- [ ] Background task/cron for Brevo polling (every 5 min)
- [ ] Full Brevo → Google Doc → Approval → PDF workflow

### P1 (Important)
- [ ] Multiple approval stages support
- [ ] Email notifications for proposal opens/clicks
- [ ] Team sharing for document editing

### P2 (Nice to Have)
- [ ] Refactor server.py into modular structure (routes/, models/, services/)
- [ ] Advanced analytics (conversion funnel, time-based trends)
- [ ] Proposal versioning
- [ ] Custom branding for exported PDFs

## API Endpoints

### Proposals
- `GET /api/proposals` - List all proposals
- `GET /api/proposals/{id}` - Get single proposal
- `POST /api/proposals` - Create proposal
- `PATCH /api/proposals/{id}` - Update proposal
- `DELETE /api/proposals/{id}` - Delete proposal
- `POST /api/generate-proposal` - AI generation

### Clauses & Templates
- `GET /api/clauses` - List clauses
- `POST /api/clauses` - Create clause
- `DELETE /api/clauses/{id}` - Delete clause
- `GET /api/templates` - List templates

### Email
- `POST /api/send-email` - Send proposal via Resend
- `GET /api/email-logs/{proposal_id}` - Get email logs
- `GET /api/track-open/{email_log_id}` - Tracking pixel
- `GET /api/track-click/{email_log_id}` - Click tracking

### Settings & Integrations
- `GET /api/settings` - Get app settings
- `POST /api/settings` - Save app settings
- `GET /api/integrations/resend/status` - Check Resend
- `GET /api/integrations/brevo/status` - Check Brevo
- `GET /api/integrations/google/status` - Check Google

### Brevo CRM
- `GET /api/brevo/opportunities` - Fetch deals
- `PATCH /api/brevo/opportunities/{id}` - Update deal
- `POST /api/webhooks/brevo` - Webhook handler
- `GET /api/brevo/pending-deals` - Pending proposal deals

### Analytics
- `GET /api/stats` - Dashboard stats
- `GET /api/analytics` - Detailed analytics

## Testing Status
- Backend: 100% (18/18 tests passed)
- Frontend: All features working
- Last test report: `/app/test_reports/iteration_4.json`
