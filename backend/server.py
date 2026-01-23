from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import io
import PyPDF2
import asyncio
import resend

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure Resend
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'proposals@yourdomain.com')

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
    clauses = await db.clauses.find({}, {"_id": 0}).to_list(1000)
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
    templates = await db.templates.find({}, {"_id": 0}).to_list(1000)
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
async def get_proposals(status: Optional[str] = None):
    query = {} if not status else {"status": status}
    proposals = await db.proposals.find(query, {"_id": 0}).to_list(1000)
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
    proposals = await db.proposals.find({}, {"_id": 0}).to_list(1000)
    
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