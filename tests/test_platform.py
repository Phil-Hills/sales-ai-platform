import sys
import os
import pytest
import asyncio
from fastapi.testclient import TestClient

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, platform_manager
from core.platform_manager import BusinessProfile

client = TestClient(app)

def test_platform_status():
    response = client.get("/api/platform/status")
    assert response.status_code == 200
    data = response.json()
    assert "profile" in data
    assert "subscription" in data

def test_configure_platform():
    new_profile = {
        "name": "Test Corp",
        "industry": "Testing",
        "agent_name": "Tester",
        "tone": "Neutral",
        "product_description": "We test things.",
        "goals": "Ensure quality.",
        "compliance_rules": "No bugs."
    }
    response = client.post("/api/platform/configure", json=new_profile)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["name"] == "Test Corp"
    
    # Verify persistence in manager
    assert platform_manager.get_profile().name == "Test Corp"

def test_subscription_limits():
    # Reset usage via API (handled by TestClient)
    client.post("/api/platform/reset_usage")
    
    # Direct manager access needs async handling
    async def run_check():
        await platform_manager.reset_usage()
        platform_manager.subscription.usage_limit = 2
        
        assert await platform_manager.check_access() is True # 1/2
        assert await platform_manager.check_access() is True # 2/2
        assert await platform_manager.check_access() is False # Limit reached
        
    asyncio.run(run_check())

def test_subscription_upgrade():
    # Upgrade via API
    client.post("/api/platform/reset_usage")
    
    async def prepare():
        platform_manager.subscription.usage_limit = 1
        await platform_manager.check_access() # 1/1
        assert await platform_manager.check_access() is False
        
    asyncio.run(prepare())
    
    # Upgrade
    client.post("/api/platform/subscribe")
    assert platform_manager.subscription.is_active is True
    
    # Should work now
    async def verify():
         assert await platform_manager.check_access() is True
         
    asyncio.run(verify())

if __name__ == "__main__":
    try:
        print("Running test_platform_status...")
        test_platform_status()
        print("✅ test_platform_status passed")
        
        print("Running test_configure_platform...")
        test_configure_platform()
        print("✅ test_configure_platform passed")
        
        print("Running test_subscription_limits...")
        test_subscription_limits()
        print("✅ test_subscription_limits passed")
        
        print("Running test_subscription_upgrade...")
        test_subscription_upgrade()
        print("✅ test_subscription_upgrade passed")
        
        print("🎉 ALL TESTS PASSED")
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
