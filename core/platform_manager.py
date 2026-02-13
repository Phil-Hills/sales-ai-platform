import json
import os
from typing import Dict, Optional, List
from pydantic import BaseModel, Field

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
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.profile = BusinessProfile(**data.get("profile", {}))
                    self.subscription = Subscription(**data.get("subscription", {}))
            except Exception as e:
                print(f"Error loading platform data: {e}")
        else:
            self._save_data()

    def _save_data(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump({
                    "profile": self.profile.model_dump(),
                    "subscription": self.subscription.model_dump()
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving platform data: {e}")

    def update_profile(self, profile_data: Dict):
        """Updates the business profile with new data."""
        # Update fields only if provided
        current_data = self.profile.model_dump()
        current_data.update(profile_data)
        self.profile = BusinessProfile(**current_data)
        self._save_data()
        return self.profile

    def get_profile(self) -> BusinessProfile:
        return self.profile

    def check_access(self) -> bool:
        """Checks if the request is allowed based on subscription."""
        if self.subscription.is_active:
            return True
        
        if self.subscription.usage_count < self.subscription.usage_limit:
            self.subscription.usage_count += 1
            self._save_data() # Persist usage increment
            return True
            
        return False

    def upgrade_subscription(self):
        """Simulates upgrading to premium."""
        self.subscription.is_active = True
        self.subscription.plan_name = "Premium"
        self._save_data()

    def reset_usage(self):
        """Resets usage count (e.g., for testing)."""
        self.subscription.usage_count = 0
        self._save_data()
