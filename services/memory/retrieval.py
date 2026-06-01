"""
services/memory/retrieval.py — Retrieves and ranks memories for context injection.
"""
import time
from loguru import logger
from services.memory.chroma_client import memory_db

def _normalize_score(value, min_val, max_val):
    """Min-max normalization."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)

def retrieve_context(query: str, project: str = None, top_k: int = 5) -> str:
    """
    Retrieves and ranks memories from all relevant collections based on a composite score.
    Returns a formatted string ready for injection into the Planner context.
    """
    if not memory_db.client:
        return ""
        
    collections_to_search = ["aura_episodic", "aura_semantic", "aura_procedural"]
    if project:
        collections_to_search.append(f"aura_project_{project}")
        
    all_results = []
    current_time = time.time()
    
    for c_name in collections_to_search:
        col = memory_db.get_collection(c_name)
        if not col:
            continue
            
        try:
            # Query top K from each collection
            res = col.query(query_texts=[query], n_results=top_k)
            
            distances = res.get("distances", [[]])[0]
            docs = res.get("documents", [[]])[0]
            metadatas = res.get("metadatas", [[]])[0]
            
            for dist, doc, meta in zip(distances, docs, metadatas):
                # 1. Similarity (Inverse of distance). Max distance in L2 is unbounded but typically < 2.0 for normalized vectors.
                # Assuming distance ~ 0.0-2.0
                sim_score = max(0, 2.0 - dist) / 2.0 
                
                # 2. Importance (1-10) -> (0-1)
                importance_score = meta.get("importance", 5) / 10.0
                
                # 3. Recency. Decay over time (e.g. 7 days half-life)
                # For simplicity, min-max normalize based on age in days.
                age_seconds = current_time - meta.get("timestamp", current_time)
                age_days = age_seconds / (24 * 3600)
                recency_score = max(0, 1.0 - (age_days / 30.0)) # 0 score if older than 30 days
                
                # Composite Formula
                composite = (sim_score * 0.6) + (importance_score * 0.2) + (recency_score * 0.2)
                
                all_results.append({
                    "text": doc,
                    "category": c_name,
                    "score": composite
                })
        except Exception as e:
            logger.debug(f"Collection {c_name} might be empty or query failed: {e}")
            
    # Sort globally across collections by composite score
    all_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = all_results[:top_k]
    
    if not top_results:
        return ""
        
    # Format for Planner
    context_str = "--- RECALLED MEMORY CONTEXT ---\n"
    for r in top_results:
        # Example: [Semantic Memory]: User prefers dark mode.
        cat_formatted = r["category"].replace("aura_", "").capitalize()
        context_str += f"[{cat_formatted} Memory]: {r['text']}\n"
    context_str += "-------------------------------"
    
    return context_str
