import pytest
from core.lead_management import LeadManager

@pytest.fixture
def lead_manager():
    return LeadManager(project_id="test-project")

def test_va_lead_scoring(lead_manager):
    lead = {
        "name": "John Doe",
        "notes": "Looking for VA loan information.",
        "status": "new"
    }
    score = lead_manager.calculate_lead_score(lead)
    assert score == 10  # Base VA score

def test_working_contact_scoring(lead_manager):
    lead = {
        "name": "Jane Smith",
        "notes": "Standard conventional loan request.",
        "status": "working - contacted"
    }
    score = lead_manager.calculate_lead_score(lead)
    assert score == 15  # Contacted milestone

def test_appointment_scoring(lead_manager):
    lead = {
        "name": "Bob Veteran",
        "notes": "Veteran borrower. Scheduled appointment for Monday.",
        "status": "qualified"
    }
    score = lead_manager.calculate_lead_score(lead)
    # 10 (VA) + 40 (Appointment/Qualified) + 10 (Length Bonus > 50 chars) = 60
    assert score == 60

def test_detailed_notes_bonus(lead_manager):
    lead = {
        "name": "Alice Green",
        "notes": "Long detailed description of financial goals and property interests in the Seattle area with a focus on jumbo loans.",
        "status": "new"
    }
    score = lead_manager.calculate_lead_score(lead)
    assert score == 10  # Bonus for >50 chars
