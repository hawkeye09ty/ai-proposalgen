from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import io
import PyPDF2
import asyncio
import resend
import json

# Google APIs
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure Resend
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'proposals@yourdomain.com')

# Google OAuth Config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

class Clause(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    category: str
    is_custom: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClauseCreate(BaseModel):
    title: str
    content: str
    category: str
    is_custom: bool = False

class Template(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    industry: str
    description: str
    prompt_template: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Proposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    project_description: str
    budget_range: str
    timeline: str
    status: str = "Draft"
    content: Optional[str] = None
    selected_clauses: List[str] = []
    deal_value: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None

class ProposalCreate(BaseModel):
    client_name: str
    project_description: str
    budget_range: str
    timeline: str
    selected_clauses: List[str] = []
    deal_value: Optional[float] = None

class ProposalUpdate(BaseModel):
    client_name: Optional[str] = None
    project_description: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None
    selected_clauses: Optional[List[str]] = None
    deal_value: Optional[float] = None

class GenerateProposalRequest(BaseModel):
    client_name: str
    project_description: str
    budget_range: str
    timeline: str
    selected_clauses: List[str] = []
    additional_requirements: Optional[str] = None
    template_id: Optional[str] = None
    uploaded_file_content: Optional[str] = None

class EmailLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proposal_id: str
    recipient_email: str
    subject: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    opened: bool = False
    opened_at: Optional[datetime] = None
    clicked: bool = False
    clicked_at: Optional[datetime] = None
    resend_email_id: Optional[str] = None

class SendEmailRequest(BaseModel):
    proposal_id: str
    recipient_email: EmailStr
    custom_message: Optional[str] = None

@api_router.get("/")
async def root():
    return {"message": "Proposal Builder API"}

@api_router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        if file.filename.endswith('.pdf'):
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        elif file.filename.endswith('.txt'):
            text = content.decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
        
        return {"content": text, "filename": file.filename}
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@api_router.post("/clauses", response_model=Clause)
async def create_clause(input: ClauseCreate):
    clause_dict = input.model_dump()
    clause_obj = Clause(**clause_dict)
    doc = clause_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.clauses.insert_one(doc)
    return clause_obj

@api_router.get("/clauses", response_model=List[Clause])
async def get_clauses():
    clauses = await db.clauses.find({}, {"_id": 0}).to_list(100)
    for clause in clauses:
        if isinstance(clause['created_at'], str):
            clause['created_at'] = datetime.fromisoformat(clause['created_at'])
    return clauses

@api_router.delete("/clauses/{clause_id}")
async def delete_clause(clause_id: str):
    result = await db.clauses.delete_one({"id": clause_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Clause not found")
    return {"message": "Clause deleted successfully"}

@api_router.get("/templates", response_model=List[Template])
async def get_templates():
    templates = await db.templates.find({}, {"_id": 0}).to_list(50)
    for template in templates:
        if isinstance(template['created_at'], str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
    return templates

@api_router.post("/proposals", response_model=Proposal)
async def create_proposal(input: ProposalCreate):
    proposal_dict = input.model_dump()
    proposal_obj = Proposal(**proposal_dict)
    doc = proposal_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('accepted_at'):
        doc['accepted_at'] = doc['accepted_at'].isoformat()
    await db.proposals.insert_one(doc)
    return proposal_obj

@api_router.get("/proposals", response_model=List[Proposal])
async def get_proposals(status: Optional[str] = None, limit: int = 100, skip: int = 0):
    query = {} if not status else {"status": status}
    proposals = await db.proposals.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    for proposal in proposals:
        if isinstance(proposal['created_at'], str):
            proposal['created_at'] = datetime.fromisoformat(proposal['created_at'])
        if isinstance(proposal['updated_at'], str):
            proposal['updated_at'] = datetime.fromisoformat(proposal['updated_at'])
        if proposal.get('accepted_at') and isinstance(proposal['accepted_at'], str):
            proposal['accepted_at'] = datetime.fromisoformat(proposal['accepted_at'])
    return proposals

@api_router.get("/proposals/{proposal_id}", response_model=Proposal)
async def get_proposal(proposal_id: str):
    proposal = await db.proposals.find_one({"id": proposal_id}, {"_id": 0})
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if isinstance(proposal['created_at'], str):
        proposal['created_at'] = datetime.fromisoformat(proposal['created_at'])
    if isinstance(proposal['updated_at'], str):
        proposal['updated_at'] = datetime.fromisoformat(proposal['updated_at'])
    if proposal.get('accepted_at') and isinstance(proposal['accepted_at'], str):
        proposal['accepted_at'] = datetime.fromisoformat(proposal['accepted_at'])
    return proposal

@api_router.patch("/proposals/{proposal_id}", response_model=Proposal)
async def update_proposal(proposal_id: str, update_data: ProposalUpdate):
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if update_dict.get('status') == 'Accepted':
        update_dict['accepted_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.proposals.update_one(
        {"id": proposal_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    updated_proposal = await db.proposals.find_one({"id": proposal_id}, {"_id": 0})
    if isinstance(updated_proposal['created_at'], str):
        updated_proposal['created_at'] = datetime.fromisoformat(updated_proposal['created_at'])
    if isinstance(updated_proposal['updated_at'], str):
        updated_proposal['updated_at'] = datetime.fromisoformat(updated_proposal['updated_at'])
    if updated_proposal.get('accepted_at') and isinstance(updated_proposal['accepted_at'], str):
        updated_proposal['accepted_at'] = datetime.fromisoformat(updated_proposal['accepted_at'])
    return updated_proposal

@api_router.delete("/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str):
    result = await db.proposals.delete_one({"id": proposal_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"message": "Proposal deleted successfully"}

@api_router.post("/generate-proposal")
async def generate_proposal(request: GenerateProposalRequest):
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="API key not configured")
        
        clauses_content = ""
        if request.selected_clauses:
            clauses = await db.clauses.find(
                {"id": {"$in": request.selected_clauses}},
                {"_id": 0}
            ).to_list(100)
            clauses_content = "\n\n".join([f"**{c['title']}**\n{c['content']}" for c in clauses])
        
        template_guidance = ""
        if request.template_id:
            template = await db.templates.find_one({"id": request.template_id}, {"_id": 0})
            if template:
                template_guidance = f"\n\nIndustry Focus: {template['industry']}\n{template['prompt_template']}"
        
        file_content_section = ""
        if request.uploaded_file_content:
            file_content_section = f"\n\nRequirements from uploaded document:\n{request.uploaded_file_content[:3000]}"
        
        additional_req = f'Additional Requirements: {request.additional_requirements}' if request.additional_requirements else ''
        clauses_section = f'Include these clauses in the proposal:\n{clauses_content}' if clauses_content else ''
        
        prompt = f"""Generate a professional business proposal with the following details:

Client Name: {request.client_name}
Project Description: {request.project_description}
Budget Range: {request.budget_range}
Timeline: {request.timeline}

{additional_req}
{file_content_section}
{template_guidance}

{clauses_section}

Please create a comprehensive, well-structured proposal that includes:
1. Executive Summary
2. Project Overview
3. Scope of Work
4. Timeline and Milestones
5. Budget and Pricing
6. Terms and Conditions (incorporating the provided clauses)
7. Next Steps

Use professional business language and maintain a persuasive yet informative tone."""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"proposal-{uuid.uuid4()}",
            system_message="You are an expert business proposal writer with years of experience creating winning proposals for B2B clients."
        )
        chat.with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return {"content": response}
    except Exception as e:
        logging.error(f"Error generating proposal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate proposal: {str(e)}")

@api_router.post("/send-email")
async def send_email(request: SendEmailRequest):
    try:
        # Get proposal
        proposal = await db.proposals.find_one({"id": request.proposal_id}, {"_id": 0})
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Create email log entry
        email_log_id = str(uuid.uuid4())
        tracking_url = f"{os.environ['REACT_APP_BACKEND_URL']}/api"
        
        # HTML email template
        custom_msg = request.custom_message if request.custom_message else "We're pleased to share our proposal for your consideration."
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0F172A; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f8f9fa; padding: 30px; }}
                .proposal {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .metadata {{ color: #666; font-size: 14px; margin: 10px 0; }}
                .button {{ background: #0F172A; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Proposal for {proposal['client_name']}</h1>
                </div>
                <div class="content">
                    <p>{custom_msg}</p>
                    
                    <div class="proposal">
                        <h2>Proposal Details</h2>
                        <div class="metadata">
                            <strong>Budget Range:</strong> {proposal['budget_range']}<br>
                            <strong>Timeline:</strong> {proposal['timeline']}<br>
                            <strong>Status:</strong> {proposal['status']}
                        </div>
                        
                        <div style="white-space: pre-wrap; margin-top: 20px;">
                            {proposal.get('content', 'Proposal content not available')[:2000]}...
                        </div>
                    </div>
                    
                    <a href="{tracking_url}/track-click/{email_log_id}" class="button">View Full Proposal</a>
                    
                    <p style="color: #666; font-size: 14px;">
                        If you have any questions or would like to discuss this proposal further, please don't hesitate to reach out.
                    </p>
                </div>
                <div class="footer">
                    <p>This is an automated email from ProposalAI</p>
                </div>
            </div>
            <img src="{tracking_url}/track-open/{email_log_id}" width="1" height="1" alt="" />
        </body>
        </html>
        """
        
        subject = f"Proposal for {proposal['client_name']}"
        
        params = {
            "from": SENDER_EMAIL,
            "to": [request.recipient_email],
            "subject": subject,
            "html": html_content
        }
        
        # Send email
        email = await asyncio.to_thread(resend.Emails.send, params)
        
        # Save email log
        email_log = EmailLog(
            id=email_log_id,
            proposal_id=request.proposal_id,
            recipient_email=request.recipient_email,
            subject=subject,
            resend_email_id=email.get("id")
        )
        
        doc = email_log.model_dump()
        doc['sent_at'] = doc['sent_at'].isoformat()
        if doc.get('opened_at'):
            doc['opened_at'] = doc['opened_at'].isoformat()
        if doc.get('clicked_at'):
            doc['clicked_at'] = doc['clicked_at'].isoformat()
        
        await db.email_logs.insert_one(doc)
        
        # Update proposal status
        await db.proposals.update_one(
            {"id": request.proposal_id},
            {"$set": {"status": "Sent", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {
            "status": "success",
            "message": f"Email sent to {request.recipient_email}",
            "email_log_id": email_log_id
        }
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@api_router.get("/track-open/{email_log_id}")
async def track_email_open(email_log_id: str):
    try:
        # Update email log
        result = await db.email_logs.update_one(
            {"id": email_log_id, "opened": False},
            {"$set": {
                "opened": True,
                "opened_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Return 1x1 transparent GIF
        gif_bytes = bytes.fromhex('47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b')
        return Response(content=gif_bytes, media_type="image/gif")
    except Exception as e:
        logging.error(f"Error tracking email open: {str(e)}")
        return Response(content=gif_bytes, media_type="image/gif")

@api_router.get("/track-click/{email_log_id}")
async def track_email_click(email_log_id: str):
    try:
        # Update email log
        await db.email_logs.update_one(
            {"id": email_log_id, "clicked": False},
            {"$set": {
                "clicked": True,
                "clicked_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Get proposal ID from email log
        email_log = await db.email_logs.find_one({"id": email_log_id}, {"_id": 0})
        
        # Redirect to frontend proposal page
        frontend_url = os.environ['REACT_APP_BACKEND_URL'].replace(':8001', ':3000')
        return Response(
            status_code=302,
            headers={"Location": f"{frontend_url}/proposals/{email_log['proposal_id']}"}
        )
    except Exception as e:
        logging.error(f"Error tracking email click: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to track click")

@api_router.get("/email-logs/{proposal_id}")
async def get_email_logs(proposal_id: str):
    try:
        email_logs = await db.email_logs.find(
            {"proposal_id": proposal_id},
            {"_id": 0}
        ).sort("sent_at", -1).to_list(100)
        
        for log in email_logs:
            if isinstance(log.get('sent_at'), str):
                log['sent_at'] = datetime.fromisoformat(log['sent_at'])
            if log.get('opened_at') and isinstance(log['opened_at'], str):
                log['opened_at'] = datetime.fromisoformat(log['opened_at'])
            if log.get('clicked_at') and isinstance(log['clicked_at'], str):
                log['clicked_at'] = datetime.fromisoformat(log['clicked_at'])
        
        return email_logs
    except Exception as e:
        logging.error(f"Error fetching email logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch email logs")

@api_router.get("/stats")
async def get_stats():
    total = await db.proposals.count_documents({})
    draft = await db.proposals.count_documents({"status": "Draft"})
    pending = await db.proposals.count_documents({"status": "Pending Review"})
    sent = await db.proposals.count_documents({"status": "Sent"})
    accepted = await db.proposals.count_documents({"status": "Accepted"})
    rejected = await db.proposals.count_documents({"status": "Rejected"})
    
    return {
        "total": total,
        "draft": draft,
        "pending_review": pending,
        "sent": sent,
        "accepted": accepted,
        "rejected": rejected
    }

@api_router.get("/analytics")
async def get_analytics():
    # Use projection to only fetch needed fields for analytics
    proposals = await db.proposals.find(
        {}, 
        {"_id": 0, "status": 1, "deal_value": 1, "created_at": 1, "accepted_at": 1}
    ).to_list(10000)
    
    total = len(proposals)
    accepted = len([p for p in proposals if p['status'] == 'Accepted'])
    acceptance_rate = (accepted / total * 100) if total > 0 else 0
    
    proposals_with_value = [p for p in proposals if p.get('deal_value')]
    avg_deal_size = sum([p['deal_value'] for p in proposals_with_value]) / len(proposals_with_value) if proposals_with_value else 0
    
    accepted_proposals = [p for p in proposals if p['status'] == 'Accepted' and p.get('accepted_at')]
    time_to_close_days = []
    for p in accepted_proposals:
        created = datetime.fromisoformat(p['created_at']) if isinstance(p['created_at'], str) else p['created_at']
        accepted = datetime.fromisoformat(p['accepted_at']) if isinstance(p['accepted_at'], str) else p['accepted_at']
        days = (accepted - created).days
        time_to_close_days.append(days)
    
    avg_time_to_close = sum(time_to_close_days) / len(time_to_close_days) if time_to_close_days else 0
    
    status_distribution = {
        "Draft": len([p for p in proposals if p['status'] == 'Draft']),
        "Pending Review": len([p for p in proposals if p['status'] == 'Pending Review']),
        "Sent": len([p for p in proposals if p['status'] == 'Sent']),
        "Accepted": accepted,
        "Rejected": len([p for p in proposals if p['status'] == 'Rejected'])
    }
    
    return {
        "acceptance_rate": round(acceptance_rate, 1),
        "avg_deal_size": round(avg_deal_size, 2),
        "avg_time_to_close": round(avg_time_to_close, 1),
        "total_proposals": total,
        "status_distribution": status_distribution,
        "total_revenue": sum([p['deal_value'] for p in proposals_with_value])
    }

# Settings Model
class AppSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: str = "ProposalAI"
    default_sender_email: str = ""
    auto_send_on_approval: bool = False
    brevo_polling_enabled: bool = True
    brevo_polling_interval: int = 5
    google_doc_template_id: str = ""
    approval_keyword: str = "APPROVED"
    notify_on_proposal_open: bool = True
    notify_on_proposal_click: bool = True

@api_router.get("/settings")
async def get_settings():
    settings = await db.settings.find_one({"_id": "app_settings"})
    if settings:
        del settings["_id"]
        return settings
    return AppSettings().model_dump()

@api_router.post("/settings")
async def save_settings(settings: AppSettings):
    try:
        settings_dict = settings.model_dump()
        await db.settings.update_one(
            {"_id": "app_settings"},
            {"$set": settings_dict},
            upsert=True
        )
        return {"status": "success", "message": "Settings saved successfully"}
    except Exception as e:
        logging.error(f"Error saving settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

# Integration Status Endpoints
@api_router.get("/integrations/resend/status")
async def get_resend_status():
    api_key = os.environ.get('RESEND_API_KEY', '')
    connected = bool(api_key and api_key != 're_123456789' and len(api_key) > 10)
    return {"connected": connected}

@api_router.get("/integrations/brevo/status")
async def get_brevo_status():
    api_key = os.environ.get('BREVO_API_KEY', '')
    if not api_key:
        return {"connected": False}
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.brevo.com/v3/account",
                headers={"api-key": api_key}
            )
            return {"connected": response.status_code == 200}
    except Exception as e:
        logging.error(f"Brevo status check failed: {str(e)}")
        return {"connected": False}

@api_router.get("/integrations/google/status")
async def get_google_status():
    # Check if Google OAuth tokens exist in database
    google_auth = await db.google_auth.find_one({"_id": "google_oauth_tokens"})
    has_credentials = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    has_tokens = google_auth is not None and google_auth.get("access_token")
    return {
        "connected": has_tokens,
        "configured": has_credentials,
        "needs_authorization": has_credentials and not has_tokens
    }

# Google OAuth Endpoints
@api_router.get("/google/auth-url")
async def get_google_auth_url():
    """Generate Google OAuth authorization URL"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")
    
    # Get the redirect URI from environment (required)
    redirect_uri = os.environ['GOOGLE_REDIRECT_URI']
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri
    )
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store state for verification
    await db.google_auth.update_one(
        {"_id": "oauth_state"},
        {"$set": {"state": state, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {"auth_url": auth_url, "state": state}

@api_router.get("/google/callback")
async def google_oauth_callback(code: str, state: Optional[str] = None):
    """Handle Google OAuth callback"""
    try:
        redirect_uri = os.environ['GOOGLE_REDIRECT_URI']
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=GOOGLE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store tokens in database
        token_data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else GOOGLE_SCOPES,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.google_auth.update_one(
            {"_id": "google_oauth_tokens"},
            {"$set": token_data},
            upsert=True
        )
        
        # Redirect to frontend settings page
        frontend_base = redirect_uri.replace('/api/google/callback', '').replace(':8001', ':3000')
        return RedirectResponse(url=f"{frontend_base}/settings?google_connected=true")
    
    except Exception as e:
        logging.error(f"Google OAuth callback error: {str(e)}")
        frontend_base = os.environ['REACT_APP_BACKEND_URL'].replace(':8001', ':3000')
        return RedirectResponse(url=f"{frontend_base}/settings?google_error={str(e)}")

async def get_google_credentials():
    """Get Google credentials from database and refresh if needed"""
    token_data = await db.google_auth.find_one({"_id": "google_oauth_tokens"})
    
    if not token_data or not token_data.get("access_token"):
        return None
    
    credentials = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", GOOGLE_CLIENT_ID),
        client_secret=token_data.get("client_secret", GOOGLE_CLIENT_SECRET),
        scopes=token_data.get("scopes", GOOGLE_SCOPES)
    )
    
    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
        
        # Update stored tokens
        await db.google_auth.update_one(
            {"_id": "google_oauth_tokens"},
            {"$set": {
                "access_token": credentials.token,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return credentials

# Google Docs Endpoints
class CreateDocRequest(BaseModel):
    template_id: str
    document_title: str
    data: Dict[str, Any]

class CreateNewDocRequest(BaseModel):
    document_title: str
    content: Optional[str] = None

@api_router.post("/google/docs/create-new")
async def create_new_google_doc(request: CreateNewDocRequest):
    """Create a brand new Google Doc with optional content"""
    credentials = await get_google_credentials()
    if not credentials:
        raise HTTPException(status_code=401, detail="Google not authorized. Please connect Google in Settings.")
    
    try:
        docs_service = build('docs', 'v1', credentials=credentials)
        
        # Create a new blank document
        doc = docs_service.documents().create(body={'title': request.document_title}).execute()
        new_doc_id = doc.get('documentId')
        
        # If content provided, add it to the document
        if request.content:
            requests = [{
                'insertText': {
                    'location': {'index': 1},
                    'text': request.content
                }
            }]
            docs_service.documents().batchUpdate(
                documentId=new_doc_id,
                body={'requests': requests}
            ).execute()
        
        # Store document metadata
        doc_record = {
            "id": str(uuid.uuid4()),
            "google_doc_id": new_doc_id,
            "title": request.document_title,
            "template_id": None,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "shared_with": [],
            "data_snapshot": {}
        }
        await db.google_docs.insert_one(doc_record)
        
        return {
            "success": True,
            "document_id": new_doc_id,
            "document_url": f"https://docs.google.com/document/d/{new_doc_id}/edit",
            "metadata_id": doc_record["id"]
        }
    
    except HttpError as e:
        logging.error(f"Google API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google API error: {str(e)}")

@api_router.post("/google/docs/create-from-template")
async def create_doc_from_template(request: CreateDocRequest):
    """Create a new Google Doc from a template and populate with data"""
    credentials = await get_google_credentials()
    if not credentials:
        raise HTTPException(status_code=401, detail="Google not authorized. Please connect Google in Settings.")
    
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        docs_service = build('docs', 'v1', credentials=credentials)
        
        # Copy the template
        copy_metadata = {'name': request.document_title}
        copied_file = drive_service.files().copy(
            fileId=request.template_id,
            body=copy_metadata
        ).execute()
        
        new_doc_id = copied_file['id']
        
        # Replace placeholders with data
        requests = []
        for placeholder, value in request.data.items():
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': f'{{{{{placeholder}}}}}',
                        'matchCase': False
                    },
                    'replaceText': str(value)
                }
            })
        
        if requests:
            docs_service.documents().batchUpdate(
                documentId=new_doc_id,
                body={'requests': requests}
            ).execute()
        
        # Store document metadata
        doc_record = {
            "id": str(uuid.uuid4()),
            "google_doc_id": new_doc_id,
            "title": request.document_title,
            "template_id": request.template_id,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "shared_with": [],
            "data_snapshot": request.data
        }
        await db.google_docs.insert_one(doc_record)
        
        return {
            "success": True,
            "document_id": new_doc_id,
            "document_url": f"https://docs.google.com/document/d/{new_doc_id}/edit",
            "metadata_id": doc_record["id"]
        }
    
    except HttpError as e:
        logging.error(f"Google API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google API error: {str(e)}")

class ShareDocRequest(BaseModel):
    document_id: str
    email: str
    role: str = "writer"  # reader, commenter, writer

@api_router.post("/google/docs/share")
async def share_google_doc(request: ShareDocRequest):
    """Share a Google Doc with a user"""
    credentials = await get_google_credentials()
    if not credentials:
        raise HTTPException(status_code=401, detail="Google not authorized")
    
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        permission = {
            'type': 'user',
            'role': request.role,
            'emailAddress': request.email
        }
        
        result = drive_service.permissions().create(
            fileId=request.document_id,
            body=permission,
            sendNotificationEmail=True
        ).execute()
        
        # Update metadata
        await db.google_docs.update_one(
            {"google_doc_id": request.document_id},
            {
                "$push": {"shared_with": request.email},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {"success": True, "permission_id": result.get("id")}
    
    except HttpError as e:
        logging.error(f"Share error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to share document: {str(e)}")

@api_router.get("/google/docs/{document_id}/comments")
async def get_doc_comments(document_id: str):
    """Get comments from a Google Doc"""
    credentials = await get_google_credentials()
    if not credentials:
        raise HTTPException(status_code=401, detail="Google not authorized")
    
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        results = drive_service.comments().list(
            fileId=document_id,
            fields="comments(id,author,content,createdTime,resolved)",
            pageSize=100
        ).execute()
        
        return {"comments": results.get("comments", [])}
    
    except HttpError as e:
        logging.error(f"Comments error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")

@api_router.post("/google/docs/{document_id}/check-approval")
async def check_doc_approval(document_id: str, approval_keyword: str = "APPROVED"):
    """Check if a document has been approved via comments"""
    credentials = await get_google_credentials()
    if not credentials:
        raise HTTPException(status_code=401, detail="Google not authorized")
    
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        results = drive_service.comments().list(
            fileId=document_id,
            fields="comments(id,content,resolved)",
            pageSize=100
        ).execute()
        
        comments = results.get("comments", [])
        approved = any(approval_keyword.upper() in c.get("content", "").upper() for c in comments)
        
        if approved:
            await db.google_docs.update_one(
                {"google_doc_id": document_id},
                {"$set": {
                    "status": "approved",
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        return {"approved": approved, "keyword": approval_keyword}
    
    except HttpError as e:
        logging.error(f"Approval check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check approval: {str(e)}")

@api_router.get("/google/docs/{document_id}/export-pdf")
async def export_doc_to_pdf(document_id: str):
    """Export a Google Doc to PDF"""
    credentials = await get_google_credentials()
    if not credentials:
        raise HTTPException(status_code=401, detail="Google not authorized")
    
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Get document title
        doc_meta = await db.google_docs.find_one({"google_doc_id": document_id})
        title = doc_meta.get("title", "document") if doc_meta else "document"
        
        # Export as PDF
        request = drive_service.files().export(
            fileId=document_id,
            mimeType='application/pdf'
        )
        pdf_content = request.execute()
        
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={title}.pdf"}
        )
    
    except HttpError as e:
        logging.error(f"PDF export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")

@api_router.get("/google/docs/list")
async def list_google_docs():
    """List all Google Docs created by the app"""
    docs = await db.google_docs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"documents": docs}

# Brevo CRM Endpoints
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')

@api_router.get("/brevo/opportunities")
async def get_brevo_opportunities(stage: Optional[str] = None):
    """Fetch opportunities from Brevo CRM"""
    if not BREVO_API_KEY:
        raise HTTPException(status_code=400, detail="Brevo API key not configured")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            params = {}
            if stage:
                params["filter[attributes.pipeline_stage]"] = stage
            
            response = await client.get(
                "https://api.brevo.com/v3/crm/deals",
                headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
                params=params
            )
            
            if response.status_code != 200:
                logging.error(f"Brevo API error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch opportunities from Brevo")
            
            return response.json()
    except httpx.RequestError as e:
        logging.error(f"Brevo request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Brevo: {str(e)}")

@api_router.patch("/brevo/opportunities/{deal_id}")
async def update_brevo_opportunity(deal_id: str, update_data: dict):
    """Update a Brevo opportunity/deal"""
    if not BREVO_API_KEY:
        raise HTTPException(status_code=400, detail="Brevo API key not configured")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.brevo.com/v3/crm/deals/{deal_id}",
                headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
                json=update_data
            )
            
            if response.status_code not in [200, 204]:
                logging.error(f"Brevo update error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to update Brevo opportunity")
            
            return {"status": "success", "message": "Opportunity updated"}
    except httpx.RequestError as e:
        logging.error(f"Brevo request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Brevo: {str(e)}")

# Webhook endpoint for Brevo
@api_router.post("/webhooks/brevo")
async def brevo_webhook(payload: dict):
    """Handle Brevo webhooks for opportunity stage changes"""
    try:
        event_type = payload.get("event")
        deal_data = payload.get("data", {})
        
        logging.info(f"Received Brevo webhook: {event_type}")
        
        # Check if deal moved to "proposal" stage
        if event_type == "deal.stage.update":
            new_stage = deal_data.get("attributes", {}).get("pipeline_stage", "").lower()
            
            if "proposal" in new_stage:
                # Store the deal for processing
                brevo_deal = {
                    "id": str(uuid.uuid4()),
                    "brevo_deal_id": deal_data.get("id"),
                    "deal_name": deal_data.get("attributes", {}).get("deal_name", "Unknown"),
                    "company_name": deal_data.get("linked_companies", [{}])[0].get("name", "Unknown"),
                    "contact_email": deal_data.get("linked_contacts", [{}])[0].get("email", ""),
                    "deal_value": deal_data.get("attributes", {}).get("amount", 0),
                    "stage": new_stage,
                    "status": "pending_doc_creation",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "raw_data": deal_data
                }
                
                await db.brevo_deals.insert_one(brevo_deal)
                logging.info(f"Created brevo deal record: {brevo_deal['id']}")
                
                return {"status": "success", "message": "Deal queued for proposal creation"}
        
        return {"status": "success", "message": "Webhook received"}
    except Exception as e:
        logging.error(f"Error processing Brevo webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

@api_router.get("/brevo/pending-deals")
async def get_pending_brevo_deals():
    """Get Brevo deals pending proposal creation"""
    deals = await db.brevo_deals.find(
        {"status": {"$in": ["pending_doc_creation", "doc_created", "pending_approval"]}},
        {"_id": 0}
    ).to_list(100)
    return deals

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

@app.on_event("startup")
async def startup_db():
    default_clauses = [
        {
            "id": str(uuid.uuid4()),
            "title": "Payment Terms",
            "content": "Payment shall be made in accordance with the agreed schedule. A 50% deposit is required upon signing, with the remaining 50% due upon project completion. Late payments may incur a 2% monthly interest charge.",
            "category": "Financial",
            "is_custom": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Intellectual Property Rights",
            "content": "Upon full payment, all intellectual property rights for the deliverables will be transferred to the Client. The Service Provider retains the right to use the project in their portfolio and marketing materials.",
            "category": "Legal",
            "is_custom": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Confidentiality",
            "content": "Both parties agree to maintain confidentiality of all proprietary information shared during the course of this project. This obligation shall survive the termination of this agreement for a period of 5 years.",
            "category": "Legal",
            "is_custom": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Warranty and Support",
            "content": "The Service Provider warrants that all deliverables will be free from defects for a period of 90 days following delivery. Support and maintenance services are available at an additional cost as outlined in a separate agreement.",
            "category": "Service",
            "is_custom": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Termination Clause",
            "content": "Either party may terminate this agreement with 30 days written notice. In the event of termination, the Client shall pay for all work completed up to the termination date. The Service Provider will deliver all completed work upon receipt of payment.",
            "category": "Legal",
            "is_custom": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Scope Change Management",
            "content": "Any changes to the project scope must be documented and agreed upon in writing by both parties. Additional work beyond the original scope will be billed at the agreed hourly rate or as a separate project phase.",
            "category": "Project Management",
            "is_custom": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    existing_clauses = await db.clauses.count_documents({})
    if existing_clauses == 0:
        await db.clauses.insert_many(default_clauses)
        logger.info("Default clauses seeded successfully")
    
    default_templates = [
        {
            "id": str(uuid.uuid4()),
            "name": "Technology Solutions",
            "industry": "Technology",
            "description": "For software development, IT consulting, and tech implementation projects",
            "prompt_template": "Focus on technical specifications, scalability, security measures, technology stack, development methodology (Agile/Scrum), testing protocols, deployment strategy, and ongoing maintenance. Emphasize innovation, efficiency gains, and ROI through technology.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Consulting Services",
            "industry": "Consulting",
            "description": "For business strategy, management consulting, and advisory services",
            "prompt_template": "Emphasize strategic value, industry expertise, proven methodologies, change management approach, stakeholder engagement, measurable outcomes, and knowledge transfer. Include case studies or similar client success stories. Focus on business transformation and strategic alignment.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Creative & Design",
            "industry": "Creative",
            "description": "For branding, marketing, design, and creative production projects",
            "prompt_template": "Highlight creative vision, brand strategy, design process, creative team credentials, portfolio examples, mood boards, creative deliverables, revision rounds, and brand guidelines. Emphasize storytelling, audience engagement, and brand differentiation.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    existing_templates = await db.templates.count_documents({})
    if existing_templates == 0:
        await db.templates.insert_many(default_templates)
        logger.info("Default templates seeded successfully")