import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .salesforce_client import get_salesforce_client
from .lead_management import LeadModel

logger = logging.getLogger("salesforce_app")

class SalesforceApp:
    """
    Higher-level abstraction for Salesforce Application operations.
    Handles Lead Sync, Task (To-Do) orchestration, and Cadence management.
    """
    
    def __init__(self):
        self.sf = get_salesforce_client()

    def sync_lead_to_model(self, sf_lead: dict) -> LeadModel:
        """Maps a Salesforce Lead record to the internal LeadModel."""
        return LeadModel(
            id=sf_lead.get("Id"),
            name=sf_lead.get("Name", f"{sf_lead.get('FirstName', '')} {sf_lead.get('LastName', '')}".strip()),
            email=sf_lead.get("Email"),
            phone=sf_lead.get("Phone") or sf_lead.get("MobilePhone"),
            company=sf_lead.get("Company", "Mortgage Services"),
            status=sf_lead.get("Status", "new"),
            source="salesforce_sync"
        )

    def orchestrate_task_from_disposition(self, lead_id: str, disposition: str, notes: str) -> Optional[str]:
        """
        Automatically creates a follow-up 'To-Do' based on the call outcome.
        - Appointment Booked -> High Priority Task for NMLS Originator.
        - Callback Requested -> Scheduled Follow-up.
        """
        subject = f"AI Follow-up: {disposition}"
        due_date = datetime.now()
        priority = "Normal"
        
        if "APPOINTMENT" in disposition.upper():
            subject = "🔥 ACTION REQUIRED: Appointment Booked via AI"
            priority = "High"
            due_date = datetime.now() + timedelta(hours=1)
        elif "CALLBACK" in disposition.upper():
            subject = "📅 Follow-up: Call Requested"
            due_date = datetime.now() + timedelta(days=1)
            
        return self.sf.create_task(
            lead_id=lead_id,
            subject=subject,
            description=f"Automated AI Disposition: {notes}",
            due_date=due_date,
            priority=priority
        )

    def trigger_cadence_step(self, lead_id: str, current_step: int) -> bool:
        """
        Manages the '11-touch' cadence logic within Salesforce.
        Increments the touch count and schedules the next interaction.
        """
        if not self.sf.is_connected:
            logger.info(f"📋 [SIMULATION] Triggering Cadence Step {current_step} for Lead {lead_id}")
            return True
            
        try:
            # Note: This assumes custom fields 'Current_Cadence_Step__c' on Lead
            self.sf.sf.Lead.update(lead_id, {
                "Current_Cadence_Step__c": current_step + 1,
                "Last_AI_Interaction__c": datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update cadence step: {e}")
            return False
