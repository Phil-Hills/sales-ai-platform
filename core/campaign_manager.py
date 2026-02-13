
import asyncio
import csv
import logging
import io
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from .salesforce_app import SalesforceApp
from .vonage_client import VonageClient

logger = logging.getLogger(__name__)

class CampaignManager:
    """
    Manages outbound calling campaigns.
    Handles CSV parsing, queuing, and dialer execution (or simulation).
    """
    
    def __init__(self):
        self.sf_app = SalesforceApp()
        self.vonage = VonageClient()
        self.active_campaign: List[Dict[str, Any]] = []
        self.is_running = False
        self.current_lead_index = 0
        self.stats = {
            "total": 0,
            "dialed": 0,
            "connected": 0,
            "appointments": 0
        }

    async def load_campaign_from_csv(self, file_content: str) -> Dict[str, Any]:
        """
        Parse CSV content and load into active campaign.
        Expects keys like: 'Primary Borrower', 'Primary Borrower: Email', 'Phone' (optional)
        """
        try:
            self.active_campaign = []
            self.current_lead_index = 0
            
            # Simple CSV parsing
            f = io.StringIO(file_content)
            reader = csv.DictReader(f)
            
            for row in reader:
                # Normalize data structure
                lead = {
                    "name": row.get("Primary Borrower") or row.get("Name", "Unknown"),
                    "email": row.get("Primary Borrower: Email") or row.get("Email", ""),
                    "phone": row.get("Phone") or row.get("Mobile", ""),
                    "city": row.get("Subject Property: Address: 1", "").split(" ")[-3] if " " in row.get("Subject Property: Address: 1", "") else row.get("City", "Unknown"),
                    "state": row.get("Subject Property: Address: State") or row.get("State", "WA"),
                    "loan_amount": row.get("Total Loan Amount") or row.get("Amount", "$0"),
                    "interest_rate": row.get("Interest Rate", "0.0%"),
                    "company": "General Services" # Default context
                }
                self.active_campaign.append(lead)
            
            self.stats["total"] = len(self.active_campaign)
            self.stats["dialed"] = 0
            self.stats["connected"] = 0
            self.stats["appointments"] = 0
            
            return {"success": True, "count": len(self.active_campaign)}
            
        except Exception as e:
            logger.error(f"Failed to load campaign: {e}")
            return {"success": False, "error": str(e)}

    async def load_campaign_from_salesforce(self, campaign_id: str) -> Dict[str, Any]:
        """
        Load leads directly from a Salesforce Campaign.
        """
        try:
            self.active_campaign = []
            self.current_lead_index = 0
            
            # Fetch from Salesforce
            sf_leads = self.sf_app.sf.get_leads_for_campaign(campaign_id)
            
            for row in sf_leads:
                # Adapt Salesforce record to internal format
                lead = self.sf_app.sync_lead_to_model(row).model_dump()
                self.active_campaign.append(lead)
            
            self.stats["total"] = len(self.active_campaign)
            self.stats["dialed"] = 0
            self.stats["connected"] = 0
            self.stats["appointments"] = 0
            
            return {"success": True, "count": len(self.active_campaign)}
            
        except Exception as e:
            logger.error(f"Failed to load Salesforce campaign: {e}")
            return {"success": False, "error": str(e)}

    async def start_campaign(self):
        """Start the async dialing process."""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._run_dialer())

    async def stop_campaign(self):
        """Stop dialing."""
        self.is_running = False

    async def _run_dialer(self):
        """Background loop to process leads."""
        logger.info("🚀 Starting Campaign Dialer...")
        
        while self.is_running and self.current_lead_index < len(self.active_campaign):
            lead = self.active_campaign[self.current_lead_index]
            self.current_lead_index += 1
            
            # 0. NMLS/TCPA Check: Do Not Call Enforcement
            if lead.get('do_not_call') or lead.get('DoNotCall'):
                logger.info(f"🚫 Skipping {lead['name']} - Do Not Call flag detected.")
                continue

            # 1. Trigger Vonage Call
            self.stats["dialed"] += 1
            logger.info(f"📞 Initiating outbound call to {lead['name']}...")
            
            # Generate NCCO based on mode
            if lead.get('type') == 'broker':
                greeting = f"Hi {lead['name']}, this is Assistant calling from the local office. I'm reaching out because we've launched some new programs that could be a huge asset for your agents' listings right now."
            else:
                greeting = f"Hello {lead['name']}, this is Assistant, an AI specialist. I'm calling to follow up on your interest."
            
            ncco = self.vonage.generate_ncco(text=greeting)
            
            call_id = self.vonage.create_outbound_call(lead['phone'], ncco)
            
            if call_id:
                logger.info(f"✅ Call active: {call_id}")
            
            # 2. Log Demo Activity (for Dashboard visibility)
            self.sf_app.sf.log_demo_activity(
                lead_name=lead['name'],
                status="Dialing...",
                company=lead['company'],
                notes=f"Vonage Call UUID: {call_id or 'SIMULATED'}"
            )
            
            # Simulate Ringing Duration
            await asyncio.sleep(random.uniform(2, 4))
            
            # 2. Simulate Outcome
            # In a real system, this would trigger Vonage and wait for webhook.
            # Here we simulate high-logic outcomes.
            
            outcomes = [
                ("Voicemail", "Left voicemail about refinance rates.", 0.4),
                ("Connected - Not Interested", "Client happy with current rate.", 0.3),
                ("Connected - Callback", "Requested callback next Tuesday.", 0.2),
                ("APPOINTMENT BOOKED", "Scheduled consultation for refinance!", 0.1)
            ]
            
            # Weighted random choice
            outcome, notes, _ = random.choices(outcomes, weights=[40, 30, 20, 10], k=1)[0]
            
            # Simulate Conversation Duration if connected
            if "Connected" in outcome or "APPOINTMENT" in outcome:
                await asyncio.sleep(random.uniform(3, 6)) # Simulate talking
            
            # 3. Log Result
            if "APPOINTMENT" in outcome:
                status = "Qualified - Appointment"
                self.stats["appointments"] += 1
                self.stats["connected"] += 1
            elif "Connected" in outcome:
                status = "Working - Contacted"
                self.stats["connected"] += 1
            else:
                status = "Open - Not Contacted"
            
            # Update Dashboard
            recording_link = f"/api/recordings/demo_{lead.get('name', 'user').replace(' ', '_')}.mp3"
            
            # Always log to demo activity for UI visibility
            self.sf_app.sf.log_demo_activity(
                lead_name=lead['name'],
                status=status,
                company=lead['company'],
                notes=notes,
                recording_url=recording_link
            )
            
            if self.sf_app.sf.is_connected:
                # Real Log (if we had IDs)
                pass
            
            # Pause before next call
            await asyncio.sleep(random.uniform(2, 5))
        
        self.is_running = False
        logger.info("🏁 Campaign Completed.")

# Singleton
_manager = None
def get_campaign_manager():
    global _manager
    if _manager is None:
        _manager = CampaignManager()
    return _manager
