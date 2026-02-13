import os
import logging
import io
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

# Core Imports
from core.agent_engine import AgentEngine
from core.lead_management import LeadManager, LeadModel
from core.research_engine import ResearchEngine
from core.vonage_client import VonageClient
from core.salesforce_app import SalesforceApp
from core.comm_orchestrator import HyperChannelOrchestrator
from core.campaign_manager import get_campaign_manager
from core.campaign_manager import get_campaign_manager
from core.salesforce_client import get_salesforce_client
from core.platform_manager import PlatformManager, BusinessProfile

load_dotenv()

# ============ LOGGING ============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("core-voice-agent")

# ============ APP SETUP ============
app = FastAPI(
    title="Sales AI Platform - Agent",
    description="Professional AI Voice Agent for Sales",
    version="4.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# ============ ORCHESTRATORS ============
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "deployment-2026-core")

platform_manager = PlatformManager()
agent_engine = AgentEngine(google_api_key=GOOGLE_API_KEY, project_id=PROJECT_ID, platform_manager=platform_manager)
lead_manager = LeadManager(project_id=PROJECT_ID)
research_engine = ResearchEngine(model_flash=agent_engine.model_flash)
vonage_client = VonageClient()
sf_app = SalesforceApp()

# Global State for Demo/Session
current_lead_id: Optional[str] = None

# ============ ROUTES ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Optional: Redirect to admin if not configured or to paywall if limit reached
    # For now, just pass the profile context
    profile = platform_manager.get_profile()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "business_name": profile.name,
        "agent_name": profile.agent_name,
        "is_premium": platform_manager.subscription.is_active
    })

@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    profile = platform_manager.get_profile()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "business_name": profile.name,
        "agent_name": profile.agent_name
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "persona": agent_engine.persona,
        "business": platform_manager.get_profile().name,
        "subscription": "active" if platform_manager.subscription.is_active else "free",
        "models": {
            "thinking": agent_engine.model_thinking is not None,
            "flash": agent_engine.model_flash is not None
        },
        "storage": "firestore" if lead_manager.use_firestore else "in-memory"
    }

# ============ PLATFORM API ============

@app.post("/api/platform/configure")
async def configure_platform(request: Request):
    data = await request.json()
    profile = await platform_manager.update_profile(data)
    # Refresh agent persona
    agent_engine.persona = profile.agent_name
    return {"status": "updated", "profile": profile.model_dump()}

@app.get("/api/platform/status")
async def platform_status():
    return {
        "profile": platform_manager.get_profile().model_dump(),
        "subscription": platform_manager.subscription.model_dump()
    }

@app.post("/api/platform/subscribe")
async def subscribe_platform():
    await platform_manager.upgrade_subscription()
    return {"status": "upgraded", "plan": "Premium"}

@app.post("/api/platform/reset_usage")
async def reset_usage():
    await platform_manager.reset_usage()
    return {"status": "reset"}

# ============ LEAD API ============

@app.get("/api/leads")
async def get_leads():
    return {"leads": lead_manager.get_all_leads()}

@app.post("/api/leads/upload")
async def upload_leads(file: UploadFile = File(...)):
    content = await file.read()
    count = lead_manager.process_csv_upload(content)
    return {"message": f"Successfully imported {count} leads", "count": count}

@app.post("/api/leads/select/{lead_id}")
async def select_lead(lead_id: str):
    global current_lead_id
    lead = lead_manager.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    current_lead_id = lead_id
    return {"status": "success", "lead": lead}

@app.post("/api/leads/clear")
async def clear_lead():
    global current_lead_id
    current_lead_id = None
    return {"status": "cleared"}

# ============ AGENT API ============

@app.post("/demo")
async def agent_chat(request: Request):
    data = await request.json()
    text = data.get("text", "")
    thinking_level = data.get("thinking_level", "medium")
    
    lead = lead_manager.get_lead(current_lead_id) if current_lead_id else None
    response = await agent_engine.get_response(text, lead, thinking_level)
    
    # Process AI-driven Salesforce Actions
    if response.get("actions") and current_lead_id:
        for action in response["actions"]:
            atype = action.get("type")
            payload = action.get("payload", {})
            try:
                if atype == "create_task":
                    sf_app.orchestrate_task_from_disposition(
                        lead_id=current_lead_id,
                        disposition=payload.get("subject", "AI Follow-up"),
                        notes=f"AI Reason: {payload.get('reason', 'N/A')}"
                    )
                elif atype == "update_cadence":
                    sf_app.trigger_cadence_step(
                        lead_id=current_lead_id,
                        current_step=payload.get("next_step", 1)
                    )
                elif atype in ["send_sms", "send_email", "send_physical_mail"]:
                    lead = lead_manager.get_lead(current_lead_id)
                    comm_orchestrator.execute_action(atype, payload, lead)
                
                logger.info(f"✅ Executed AI Action: {atype}")
            except Exception as ae:
                logger.error(f"❌ Failed to execute AI action {atype}: {ae}")

    if current_lead_id:
        lead_manager.save_conversation(current_lead_id, "user", text)
        lead_manager.save_conversation(current_lead_id, "assistant", response["text"])
        
    return response

@app.post("/api/pitch")
async def generate_pitch():
    if not current_lead_id:
        raise HTTPException(status_code=400, detail="No lead selected")
    
    lead = lead_manager.get_lead(current_lead_id)
    prompt = f"Generate a professional, warm 30-second phone pitch for {lead['name']} from {lead['company']}. Highlight our mortgage expertise and service advantage. COMPLIANCE: Do not quote specific interest rates or APRs; focus on service and expertise."
    
    response = await agent_engine.get_response(prompt, lead, thinking_level="high")
    return {"pitch": response["text"]}

# ============ RESEARCH API ============

@app.post("/api/research")
async def research_company(request: Request):
    data = await request.json()
    company = data.get("company")
    if not company:
        raise HTTPException(status_code=400, detail="Company name required")
    return await research_engine.research_company(company)

# ============ CAMPAIGN API ============

@app.get("/api/campaigns/status")
async def campaign_status():
    manager = get_campaign_manager()
    return {
        "is_running": manager.is_running,
        "stats": manager.stats,
        "progress": f"{manager.current_lead_index}/{len(manager.active_campaign)}"
    }

@app.post("/api/campaigns/start")
async def start_campaign():
    manager = get_campaign_manager()
    await manager.start_campaign()
    return {"status": "started"}

@app.post("/api/campaigns/stop")
async def stop_campaign():
    manager = get_campaign_manager()
    await manager.stop_campaign()
    return {"status": "stopped"}

# ============ UTILITY API ============

@app.post("/api/tts")
async def text_to_speech(request: Request):
    data = await request.json()
    text = data.get("text", "")
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    
    if not api_key:
        raise HTTPException(status_code=500, detail="TTS not configured")
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            }
        )
        
    if resp.status_code == 200:
        return StreamingResponse(io.BytesIO(resp.content), media_type="audio/mpeg")
    
    raise HTTPException(status_code=resp.status_code, detail="TTS generation failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
