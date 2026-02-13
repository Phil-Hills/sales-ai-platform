import os
import glob
import json
import logging
import msgpack
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("research_engine")

class ResearchEngine:
    """
    Handles company research and knowledge retrieval.
    Integrates Gemini Google Search grounding and Q-Memory protocol.
    """
    
    def __init__(self, model_flash: Any, model_local: Optional[Any] = None):
        self.model_flash = model_flash
        self.model_local = model_local
        self.research_cache: Dict[str, dict] = {}
        self.q_memory: Dict[str, Any] = {}
        
    def load_qmem(self, path: str) -> int:
        """Loads QMem binary knowledge base atoms."""
        count = 0
        try:
            p = Path(path)
            files = glob.glob(str(p / "**/*.qmem"), recursive=True) if p.is_dir() else [p]
            
            for fpath in files:
                try:
                    with open(fpath, 'rb') as f:
                        f.read(32) # Skip header
                        payload = f.read()
                        data = msgpack.unpackb(payload, raw=False, strict_map_key=False)
                        
                        if 'coordinates' in data:
                            for coord in data['coordinates']:
                                subject = coord.get('subject', '').lower()
                                if subject:
                                    if subject not in self.q_memory:
                                        self.q_memory[subject] = []
                                    self.q_memory[subject].append(coord)
                                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to load QMem {fpath}: {e}")
                    
            logger.info(f"🧠 Loaded {count} knowledge atoms from Q-Memory")
            return count
        except Exception as e:
            logger.error(f"QMem loader failed: {e}")
            return 0

    async def research_company(self, company_name: str) -> dict:
        """Researched company using Gemini + Search Tool or Q-Memory fallback."""
        # 1. Cache Hit
        if company_name in self.research_cache:
            return self.research_cache[company_name]
            
        # 2. Q-Memory Hit
        q_key = company_name.lower().replace(" ", "_")
        if q_key in self.q_memory:
            atoms = self.q_memory[q_key]
            knowledge_text = "\n".join([f"- {a.get('template', '')}" for a in atoms])
            return {
                "company": company_name,
                "summary": f"Brain Recovery: {knowledge_text}",
                "source": "Q-Memory",
                "tsig": f"qmem_{datetime.now().timestamp()}"
            }

        # 3. Live Research
        if not self.model_flash:
            return {"error": "Research tool unavailable"}

        prompt = f"Research the company '{company_name}'. Return JSON: summary, news, leadership."
        
        try:
            response = self.model_flash.generate_content(prompt)
            data = self._parse_json(response.text)
            data["company"] = company_name
            self.research_cache[company_name] = data
            return data
        except Exception as e:
            logger.error(f"Flash research failed: {e}")
            return {"error": str(e)}

    def _parse_json(self, text: str) -> dict:
        """Utility to extract JSON from markdown/text."""
        try:
            if "```json" in text:
                text = text.replace("```json", "").replace("```", "")
            return json.loads(text)
        except:
            return {"summary": text, "news": [], "leadership": ""}
