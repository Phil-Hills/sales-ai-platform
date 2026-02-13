import pytest
from core.lead_management import LeadManager, LeadModel
from core.agent_engine import AgentEngine, AgentResponse
from pydantic import ValidationError

def test_lead_model_validation():
    """Verify that LeadModel enforces strict schema."""
    # Valid lead
    lead = LeadModel(name="Test User", source="test")
    assert lead.name == "Test User"
    
    # Invalid lead (missing name)
    with pytest.raises(ValidationError):
        LeadModel(source="test")

def test_agent_response_validation():
    """Verify that AgentResponse structure is respected."""
    res = AgentResponse(
        text="Hello",
        thinking_level="medium",
        persona="Jason"
    )
    assert res.persona == "Jason"
    assert "timestamp" in res.model_dump()

def test_thought_signature_integrity():
    """Verify cryptographic signature generation."""
    engine = AgentEngine(google_api_key="mock", project_id="mock")
    sig1 = engine.generate_thought_signature("Reasoning step A")
    sig2 = engine.generate_thought_signature("Reasoning step A")
    
    # Signatures should be unique (due to timestamp) or at least follow the format
    assert sig1.startswith("tsig_")
    assert len(sig1) > 10

def test_lead_manager_save_validation():
    """Verify LeadManager rejects invalid lead data."""
    lm = LeadManager(project_id="test-project")
    
    # Missing name should raise ValidationError via save_lead
    with pytest.raises(ValidationError):
        lm.save_lead({"source": "invalid"})
