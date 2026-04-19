"""
RecSys ML Platform — Evaluation Metrics.

Implements standard ranking and recommendation evaluation metrics:
NDCG@K, Precision@K, Recall@K, MAP, Coverage, and Diversity.
"""

import math
from typing import List, Dict, Set

def dcg_at_k(predictions: List[str], actuals: Set[str], k: int) -> float:
    """Discounted Cumulative Gain at K."""
    dcg = 0.0
    for i, item in enumerate(predictions[:k]):
        if item in actuals:
            dcg += 1.0 / math.log2(i + 2)
    return dcg

def ndcg_at_k(predictions: List[str], actuals: Set[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K."""
    if not actuals:
        return 0.0
    
    # Ideal DCG is when all actuals are at the top
    idcg = 0.0
    for i in range(min(len(actuals), k)):
        idcg += 1.0 / math.log2(i + 2)
        
    dcg = dcg_at_k(predictions, actuals, k)
    return dcg / idcg if idcg > 0 else 0.0

def precision_at_k(predictions: List[str], actuals: Set[str], k: int) -> float:
    """Precision at K."""
    if not predictions[:k]:
        return 0.0
    hits = sum(1 for item in predictions[:k] if item in actuals)
    return hits / float(min(k, len(predictions)))

def recall_at_k(predictions: List[str], actuals: Set[str], k: int) -> float:
    """Recall at K."""
    if not actuals:
        return 0.0
    hits = sum(1 for item in predictions[:k] if item in actuals)
    return hits / float(len(actuals))

def average_precision(predictions: List[str], actuals: Set[str]) -> float:
    """Average Precision."""
    if not actuals:
        return 0.0
        
    ap = 0.0
    hits = 0
    for i, item in enumerate(predictions):
        if item in actuals:
            hits += 1
            ap += hits / (i + 1.0)
            
    return ap / float(len(actuals))

def mean_average_precision(predictions_list: List[List[str]], actuals_list: List[Set[str]]) -> float:
    """Mean Average Precision across multiple users."""
    ap_sum = 0.0
    valid_users = 0
    
    for preds, actuals in zip(predictions_list, actuals_list):
        if actuals:
            ap_sum += average_precision(preds, actuals)
            valid_users += 1
            
    return ap_sum / valid_users if valid_users > 0 else 0.0

def coverage(all_predictions: List[List[str]], item_catalog: Set[str]) -> float:
    """Percentage of catalog items recommended at least once."""
    if not item_catalog:
        return 0.0
        
    recommended_items = set()
    for preds in all_predictions:
        recommended_items.update(preds)
        
    return len(recommended_items.intersection(item_catalog)) / float(len(item_catalog))

def diversity(predictions: List[Dict], similarity_func) -> float:
    """
    Intra-list diversity metric. Average (1 - similarity) between all pairs
    in a prediction list.
    """
    if len(predictions) < 2:
        return 1.0
        
    div_sum = 0.0
    pairs = 0
    
    for i in range(len(predictions)):
        for j in range(i + 1, len(predictions)):
            sim = similarity_func(predictions[i], predictions[j])
            div_sum += (1.0 - sim)
            pairs += 1
            
    return div_sum / pairs if pairs > 0 else 1.0
