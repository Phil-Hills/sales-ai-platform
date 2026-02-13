import os
import logging
import vonage
from typing import List, Dict, Any, Optional

logger = logging.getLogger("vonage_client")

class VonageClient:
    """
    Handles telephony operations via Vonage Voice API.
    Responsible for call triggering, NCCO generation, and event handling.
    """
    
    def __init__(self):
        self.api_key = os.getenv("VONAGE_API_KEY")
        self.api_secret = os.getenv("VONAGE_API_SECRET")
        self.application_id = os.getenv("VONAGE_APPLICATION_ID")
        self.private_key_path = os.getenv("VONAGE_PRIVATE_KEY_PATH", "private.key")
        self.from_number = os.getenv("VONAGE_FROM_NUMBER")
        
        self.client = self._initialize_client()

    def _initialize_client(self) -> Optional[vonage.Client]:
        """Initializes the Vonage client using provided credentials."""
        if not all([self.api_key, self.application_id]):
            logger.warning("⚠️ Vonage credentials missing. Telephony in simulation mode.")
            return None
            
        try:
            return vonage.Client(
                key=self.api_key,
                secret=self.api_secret,
                application_id=self.application_id,
                private_key=self.private_key_path
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vonage client: {e}")
            return None

    def generate_ncco(self, text: str, voice_name: str = "Kimberly") -> List[Dict[str, Any]]:
        """Generates a standard NCCO for the voice agent interaction."""
        return [
            {
                "action": "talk",
                "text": text,
                "voiceName": voice_name
            },
            {
                "action": "connect",
                "eventUrl": [f"{os.getenv('APP_URL', '')}/webhooks/event"],
                "endpoint": [
                    {
                        "type": "websocket",
                        "uri": f"{os.getenv('WS_URL', '')}/socket",
                        "content-type": "audio/l16;rate=16000"
                    }
                ]
            }
        ]

    def create_outbound_call(self, to_number: str, ncco: List[Dict[str, Any]]) -> Optional[str]:
        """Triggers an outbound call with the specified NCCO."""
        if not self.client:
            logger.info(f"📋 [SIMULATION] Dialing {to_number} with NCCO: {ncco}")
            return "sim_uuid_12345"
            
        try:
            response = self.client.voice.create_call({
                'to': [{'type': 'phone', 'number': to_number}],
                'from': {'type': 'phone', 'number': self.from_number},
                'ncco': ncco
            })
            return response.get('uuid')
        except Exception as e:
            logger.error(f"❌ Failed to trigger outbound call: {e}")
            return None
