from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProposalCreate(BaseModel):
    client_name: str
    project_description: str
    budget_range: str
    timeline: str
    selected_clauses: List[str] = []

class ProposalUpdate(BaseModel):
    client_name: Optional[str] = None
    project_description: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None
    selected_clauses: Optional[List[str]] = None

class GenerateProposalRequest(BaseModel):
    client_name: str
    project_description: str
    budget_range: str
    timeline: str
    selected_clauses: List[str] = []
    additional_requirements: Optional[str] = None

@api_router.get("/")
async def root():
    return {"message": "Proposal Builder API"}

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

@api_router.post("/proposals", response_model=Proposal)
async def create_proposal(input: ProposalCreate):
    proposal_dict = input.model_dump()
    proposal_obj = Proposal(**proposal_dict)
    doc = proposal_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
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
    return proposal

@api_router.patch("/proposals/{proposal_id}", response_model=Proposal)
async def update_proposal(proposal_id: str, update_data: ProposalUpdate):
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
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
        
        additional_req = f'Additional Requirements: {request.additional_requirements}' if request.additional_requirements else ''
        clauses_section = f'Include these clauses in the proposal:\n{clauses_content}' if clauses_content else ''
        
        prompt = f"""Generate a professional business proposal with the following details:

Client Name: {request.client_name}
Project Description: {request.project_description}
Budget Range: {request.budget_range}
Timeline: {request.timeline}

{additional_req}

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

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
    existing_count = await db.clauses.count_documents({})
    if existing_count == 0:
        await db.clauses.insert_many(default_clauses)
        logger.info("Default clauses seeded successfully")