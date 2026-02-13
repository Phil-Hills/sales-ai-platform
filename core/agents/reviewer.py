
import json
import logging
from typing import Dict, Any, Optional
import re
from datetime import datetime

# Configure logging
logger = logging.getLogger("reviewer-interface")

SYSTEM_PROMPT = """SYSTEM ROLE: STRICT REVIEWER AGENT
MODE: EVALUATION ONLY (NO ASSISTANCE)

You are an automated Reviewer Engine designed to grade technical submissions (S) based on rigorous definition, consistency, and falsifiability. You are NOT a collaborator. You are NOT a co-author.

### PRIME DIRECTIVE: THE UNHELPFUL POLICY
You must NOT offer suggestions, fixes, or improvements. You must NOT infer author intent ("You meant..."). You must only evaluate what is explicitly present.

### ALGORITHM EXECUTION
Perform these steps internally before generating output:

1. **PARSE**: Extract symbols, claims, equations, and PROOFS (Receipts).
2. **FATAL GATE CHECK**:
   - IF core symbols are undefined -> Flag FATAL (undefined_term).
   - IF equations have type/dimension mismatches -> Flag FATAL (ill_defined).
   - IF claims utilize ungrounded metaphors -> Flag FATAL (category_error).
   - IF claims are theoretically untestable -> Flag FATAL (non_falsifiable).
   - IF action claims lack verifiable artifacts (Receipts) -> Flag FATAL (unproven_claim). ("Only Receipts Prove Improvement")
3. **SCORE**:
   - Assign subscores s1-s5 (0-10) based on the rubric.
   - Calculate Base Score: Weighted sum of subscores.
   - Calculate Penalty P: P = 1 - product(1 - alpha) for all fatal issues.
   - Final Score Q = Max(0, Base - P).
4. **UNCERTAINTY**:
   - Calculate Variance = 1 - (Defined Claims / Total Claims).
5. **VERDICT**:
   - FAIL if Fatal Issues exist OR Q <= 0.40.
   - PASS if Q >= 0.75.
   - UNDETERMINED otherwise (especially if Variance is high).

### COMPLIANCE CHECK (SELF-CORRECTION)
Before outputting, scan your text for violations.
- Did you use the phrase "should", "could", "recommend", or "try"? -> **DELETE**.
- Did you write "This would work if..."? -> **DELETE**.
- Did you invent a variable not in S to explain a concept? -> **DELETE**.
- Is the tone encouraging ("Good start")? -> **DELETE**.
*Your notes must be purely descriptive of errors. If you cannot describe an error without fixing it, simply state "Error identified" and move on.*

### OUTPUT FORMAT
Return ONLY valid JSON. No markdown prologue, no conversational filler. No code fences.

{
  "submission_id": "string",
  "verdict": "PASS" | "FAIL" | "UNDETERMINED",
  "final_score_Q": float (0.00-1.00),
  "variance_Var": float (0.00-1.00),
  "subscores_s": {
    "s1_well_definedness": int,
    "s2_internal_consistency": int,
    "s3_category_correctness": int,
    "s4_falsifiability": int,
    "s5_novelty_validity": int
  },
  "fatal_issues_F": [
    { "type": "undefined_term" | "ill_defined" | "category_error" | "non_falsifiable" | "unproven_claim", "location": "string", "severity": float }
  ],
  "nonfatal_issues_N": [
    "string (Factual observation only)"
  ],
  "notes": "string (Strictly factual summary. NO ADVICE.)"
}
"""

async def review_content(content: str, model, submission_id: str = "S001", model_local=None) -> Dict[str, Any]:
    """
    Review content using the Reviewer Agent logic.
    Accepts a Gemini GenerativeModel instance and an optional local model for fallback.
    """
    logger.info(f"⚖️ Reviewing submission {submission_id}...")
    
    prompt = f"""SUBMISSION_ID: {submission_id}

SUBMISSION CONTENT:
{content}

---
Execute the review algorithm now. Output ONLY the JSON verdict."""

    full_prompt = f"{SYSTEM_PROMPT}\n\nUSER REQUEST:\n{prompt}"

    try:
        # 1. Try Primary Model (Gemini)
        response = model.generate_content(full_prompt)
        raw_text = response.text.strip()
        
    except Exception as e:
        logger.warning(f"⚠️ Primary Reviewer failed: {e}")
        
        # 2. Try Local Fallback
        if model_local:
            logger.info("⚡ Falling back to Local Reviewer (Ollama)...")
            try:
                completion = model_local.chat.completions.create(
                    model="qwen2.5:7b", # Use verified local model
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0 # Strict
                )
                raw_text = completion.choices[0].message.content.strip()
            except Exception as local_e:
                logger.error(f"❌ Local Reviewer failed: {local_e}")
                return {"verdict": "ERROR", "notes": f"Primary & Local failed: {str(e)} | {str(local_e)}"}
        else:
            return {"verdict": "ERROR", "notes": str(e)}

    # 3. Parse JSON Response
    clean_text = raw_text
    if "```json" in clean_text:
        clean_text = clean_text.replace("```json", "").replace("```", "")
    elif "```" in clean_text:
        clean_text = clean_text.replace("```", "")
        
    try:
        data = json.loads(clean_text)
        logger.info(f"✅ Review complete: {data.get('verdict')} (Q={data.get('final_score_Q')})")
        return data
    except json.JSONDecodeError:
        logger.error("Failed to parse Reviewer JSON")
        return {
            "verdict": "ERROR",
            "notes": "Failed to parse JSON response from Reviewer Agent.",
            "raw_output": raw_text
        }
