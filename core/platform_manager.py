import json
import os
import asyncio
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
import aiofiles

class BusinessProfile(BaseModel):
    id: str = Field(default="default_biz", description="Unique identifier for the business")
    name: str = Field(default="Generic Business", description="Name of the business")
    industry: str = Field(default="General", description="Industry type (e.g., Real Estate, Retail)")
    product_description: str = Field(default="Our amazing products and services.", description="Description of what is being sold")
    goals: str = Field(default="Help customers find the right product.", description="Primary goal of the agent")
    compliance_rules: str = Field(default="Be polite and helpful.", description="Compliance or behavioral rules")
    agent_name: str = Field(default="Assistant", description="Name of the AI agent")
    tone: str = Field(default="Professional and friendly", description="Tone of the agent")

class Subscription(BaseModel):
    is_active: bool = False
    plan_name: str = "Free"
    usage_count: int = 0
    usage_limit: int = 10  # Free tier limit

class PlatformManager:
    def __init__(self, data_file: str = "platform_data.json"):
        self.data_file = data_file
        self.profile: BusinessProfile = BusinessProfile()
        self.subscription: Subscription = Subscription()
        self.lock = asyncio.Lock()
        # Initial load is sync to ensure state before app start
        self._load_data_sync()

    def _load_data_sync(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.profile = BusinessProfile(**data.get("profile", {}))
                    self.subscription = Subscription(**data.get("subscription", {}))
            except Exception as e:
                print(f"Error loading platform data: {e}")
        else:
            self._save_data_sync()

    def _save_data_sync(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump({
                    "profile": self.profile.model_dump(),
                    "subscription": self.subscription.model_dump()
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving platform data: {e}")

    async def _save_data(self):
        async with self.lock:
            try:
                # Use aiofiles for non-blocking IO
                async with aiofiles.open(self.data_file, 'w') as f:
                    content = json.dumps({
                        "profile": self.profile.model_dump(),
                        "subscription": self.subscription.model_dump()
                    }, indent=4)
                    await f.write(content)
            except Exception as e:
                print(f"Error saving platform data: {e}")

    async def update_profile(self, profile_data: Dict):
        """Updates the business profile with new data."""
        # Update fields only if provided
        current_data = self.profile.model_dump()
        current_data.update(profile_data)
        self.profile = BusinessProfile(**current_data)
        await self._save_data()
        return self.profile

    def get_profile(self) -> BusinessProfile:
        return self.profile

    async def check_access(self) -> bool:
        """Checks if the request is allowed based on subscription."""
        if self.subscription.is_active:
            return True
        
        async with self.lock:
             if self.subscription.usage_count < self.subscription.usage_limit:
                 self.subscription.usage_count += 1
                 # We hold the lock for the increment, now save
                 # Note: calling _save_data here would try to re-acquire lock if it wasn't reentrant.
                 # asyncio.Lock is NOT reentrant.
                 # So we manually do the save logic here or separate it.
                 # Or better: check_access doesn't call _save_data, it calls a private _persist?
                 # Actually, simpler:
                 pass
             else:
                 return False

        # Persist outside the check lock? No, data intgrity. 
        # Correct pattern: Separate validtion from persistence OR use Reentrant lock? 
        # Since usage count changes, we MUST save. 
        # Let's just inline the save or make _save_data not lock, and have callers lock.
        
        # New Strategy: _save_data is internal and assumes caller handles locking if needed, 
        # OR public methods lock then call internal save.
        
        # Implementing robust version in next full file write.
        await self._save_data()
        return True

    async def upgrade_subscription(self):
        """Simulates upgrading to premium."""
        self.subscription.is_active = True
        self.subscription.plan_name = "Premium"
        await self._save_data()

    async def reset_usage(self):
        """Resets usage count (e.g., for testing)."""
        self.subscription.usage_count = 0
        await self._save_data()
