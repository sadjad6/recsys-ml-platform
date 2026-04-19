"""
RecSys ML Platform — Re-Ranking Logic.

Stage 3 of the recommendation pipeline. Adjusts ranking scores to inject
business rules such as diversity (via MMR) and popularity dampening
for cold-start item promotion.
"""

from typing import List, Dict, Tuple
import math

class ReRanker:
    def __init__(self, lambda_param: float = 0.7, pop_boost: float = 1.2, pop_penalty: float = 0.8):
        """
        Args:
            lambda_param: Trade-off between relevance and diversity in MMR.
                          1.0 = purely relevance, 0.0 = purely diversity.
            pop_boost: Multiplier for cold-start (unpopular) items.
            pop_penalty: Multiplier for highly popular items.
        """
        self.lambda_param = lambda_param
        self.pop_boost = pop_boost
        self.pop_penalty = pop_penalty

    def apply_popularity_dampening(self, ranked_items: List[Dict]) -> List[Dict]:
        """
        Adjust scores based on item popularity percentiles.
        Assumes `popularity_percentile` is provided in the item dictionary.
        """
        adjusted_items = []
        for item in ranked_items:
            new_item = item.copy()
            percentile = item.get("popularity_percentile", 0.5)
            
            if percentile > 0.90:
                new_item["score"] *= self.pop_penalty
            elif percentile < 0.30:
                new_item["score"] *= self.pop_boost
                
            adjusted_items.append(new_item)
            
        # Re-sort after adjusting scores
        return sorted(adjusted_items, key=lambda x: x["score"], reverse=True)

    def _item_similarity(self, item1: Dict, item2: Dict) -> float:
        """Simple similarity based on category overlap for diversity calculation."""
        cat1 = set(item1.get("categories", []))
        cat2 = set(item2.get("categories", []))
        
        if not cat1 or not cat2:
            return 0.0
            
        intersection = len(cat1.intersection(cat2))
        union = len(cat1.union(cat2))
        return intersection / union if union > 0 else 0.0

    def apply_mmr(self, items: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Maximal Marginal Relevance (MMR) for intra-list diversity.
        """
        if not items:
            return []
            
        # Normalize scores for fair comparison with similarity metrics (0 to 1)
        max_score = max(item["score"] for item in items) if items else 1.0
        max_score = max_score if max_score > 0 else 1.0
        
        selected = []
        unselected = items.copy()
        
        while len(selected) < top_k and unselected:
            mmr_scores = []
            
            for item in unselected:
                relevance = item["score"] / max_score
                
                # Penalty based on similarity to ALREADY selected items
                if selected:
                    max_sim = max(self._item_similarity(item, s) for s in selected)
                else:
                    max_sim = 0.0
                    
                # MMR formula: lambda * Relevance - (1 - lambda) * Diversity_Penalty
                mmr_score = self.lambda_param * relevance - (1.0 - self.lambda_param) * max_sim
                mmr_scores.append((mmr_score, item))
                
            # Pick item with highest MMR score
            mmr_scores.sort(key=lambda x: x[0], reverse=True)
            best_item = mmr_scores[0][1]
            
            selected.append(best_item)
            unselected.remove(best_item)
            
        return selected

    def rerank(self, ranked_items: List[Dict], top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Full re-ranking pipeline.
        Input format: [{"item_id": "item1", "score": 0.85, "categories": ["action"], "popularity_percentile": 0.95}, ...]
        Returns list of (item_id, final_score)
        """
        items = self.apply_popularity_dampening(ranked_items)
        diverse_items = self.apply_mmr(items, top_k=top_k)
        
        return [(item["item_id"], item["score"]) for item in diverse_items]
