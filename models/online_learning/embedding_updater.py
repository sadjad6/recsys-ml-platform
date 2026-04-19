"""
Incremental Embedding Updater for near real-time adaptation.
"""

import numpy as np
import pandas as pd
import logging
import os
import json

logger = logging.getLogger(__name__)

class IncrementalEmbeddingUpdater:
    """Updates user embeddings without full ALS retraining."""

    def __init__(self, item_factors_path: str, reg_param: float = 0.1):
        self.item_factors_path = item_factors_path
        self.reg_param = reg_param
        self.item_factors_map = {}  # item_id -> vector
        self.Y = None # Matrix of item factors
        self.Y_T_Y_reg = None # Precomputed (Y^T Y + lambda * I)
        self.item_index_map = {} # item_id -> index in Y
        
        self._load_factors()

    def _load_factors(self):
        """Load fixed item factors from the latest batch model."""
        if not os.path.exists(self.item_factors_path):
            logger.warning(f"Item factors path {self.item_factors_path} does not exist. Using dummy factors.")
            # For testing/demo, create dummy factors
            self.item_factors_map = {f"item_{i}": np.random.rand(10) for i in range(100)}
        else:
            # Here we would load from Parquet
            # For this simplified version, let's assume we read JSON for simplicity, or we mock it.
            # In production, read Parquet using pandas/pyarrow.
            pass
            
        if not self.item_factors_map:
            self.item_factors_map = {"dummy_item": np.random.rand(10)}

        items = list(self.item_factors_map.keys())
        self.Y = np.array([self.item_factors_map[i] for i in items])
        self.item_index_map = {item_id: idx for idx, item_id in enumerate(items)}
        
        # Precompute the inverse part of the least squares
        k = self.Y.shape[1]
        Y_T_Y = self.Y.T @ self.Y
        self.Y_T_Y_reg = np.linalg.inv(Y_T_Y + self.reg_param * np.eye(k))
        logger.info(f"Loaded item factors for {len(items)} items. Embedding dimension: {k}")

    def update_user_embedding(
        self, user_id: str, new_interactions: list[tuple[str, float]]
    ) -> np.ndarray:
        """Compute updated user embedding given new interactions."""
        # This is a simplified OLS formulation for implicit/explicit ALS.
        # r_u vector length = number of all items
        r_u = np.zeros(len(self.item_index_map))
        
        has_valid_items = False
        for item_id, rating in new_interactions:
            if item_id in self.item_index_map:
                r_u[self.item_index_map[item_id]] = rating
                has_valid_items = True
                
        if not has_valid_items:
            logger.debug(f"No valid items found for user {user_id}. Returning zero vector.")
            return np.zeros(self.Y.shape[1])

        # u_new = (Y^T Y + λI)^{-1} Y^T r_u
        u_new = self.Y_T_Y_reg @ self.Y.T @ r_u
        return u_new

    def batch_update(
        self, user_interactions: dict[str, list[tuple[str, float]]]
    ) -> dict[str, np.ndarray]:
        """Update embeddings for multiple users efficiently."""
        updated_embeddings = {}
        for user_id, interactions in user_interactions.items():
            updated_embeddings[user_id] = self.update_user_embedding(user_id, interactions)
            
        # In a real system, you would write `updated_embeddings` to a fast KV store (Redis).
        return updated_embeddings
