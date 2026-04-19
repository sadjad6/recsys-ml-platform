"""
Hash-based assignment logic for A/B testing.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

def assign_user_to_group(user_id: str, experiment_id: str, traffic_pct: int) -> str:
    """
    Deterministic hash-based assignment.

    1. Compute hash: hashlib.sha256(f"{user_id}:{experiment_id}").hexdigest()
    2. Convert first 8 hex chars to int
    3. Bucket = hash_int % 100
    4. If bucket >= traffic_pct → "excluded" (not in experiment)
    5. If bucket < traffic_pct / 2 → "control"
    6. Else → "treatment"
    """
    hash_input = f"{user_id}:{experiment_id}".encode("utf-8")
    hash_hex = hashlib.sha256(hash_input).hexdigest()
    
    # Use first 8 characters for the hash integer
    hash_int = int(hash_hex[:8], 16)
    bucket = hash_int % 100
    
    logger.debug(f"Assignment for {user_id} in {experiment_id}: bucket {bucket} (traffic {traffic_pct})")
    
    if bucket >= traffic_pct:
        return "excluded"
    
    if bucket < traffic_pct / 2:
        return "control"
    else:
        return "treatment"
