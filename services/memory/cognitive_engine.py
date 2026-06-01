"""
services/memory/cognitive_engine.py — Evaluates importance and deduplicates memories.
"""
import time
import uuid
import json
from loguru import logger
from groq import Groq
from core.config_loader import config
from services.memory.chroma_client import memory_db

class CognitiveEngine:
    def __init__(self):
        self.client = None
        self._model = config.get("brain.llm_model", "llama-3.1-8b-instant")
        
    def _init_client(self):
        if self.client is None:
            api_key = config.groq_api_key()
            if api_key:
                self.client = Groq(api_key=api_key)

    def evaluate_importance(self, memory_text: str) -> int:
        """Uses LLM to rate importance of memory from 1 to 10."""
        self._init_client()
        if not self.client:
            return 5 # Default fallback
            
        prompt = f"""
You are the Cognitive Engine for AURA. 
Rate the importance of the following memory on a scale of 1 to 10.
1 = Trivial, temporary (e.g. "I opened notepad", "current weather is 70F")
5 = Moderate, good for context (e.g. "User likes dark mode")
10 = Critical, architecture rules, passwords, system directives (e.g. "Never use rm -rf")

Memory: "{memory_text}"

Return ONLY a valid JSON object: {{"score": 5}}
"""
        try:
            resp = self.client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = json.loads(resp.choices[0].message.content)
            return int(data.get("score", 5))
        except Exception as e:
            logger.error(f"Importance scoring failed: {e}")
            return 5

    def store_memory(self, category: str, text: str, project: str = None) -> bool:
        """Stores a memory if importance > 5, handles deduplication."""
        # 1. Score
        score = self.evaluate_importance(text)
        if score < 5:
            logger.info(f"Memory '{text[:30]}...' rejected. Importance too low ({score}/10).")
            return False
            
        # 2. Get Collection
        collection_name = f"aura_{category}" if not project else f"aura_project_{project}"
        collection = memory_db.get_collection(collection_name)
        if not collection:
            return False
            
        # 3. Deduplication (Check for highly similar existing memories)
        results = collection.query(
            query_texts=[text],
            n_results=1
        )
        
        # ChromaDB default metric is L2. Small distance = highly similar.
        # Threshold for duplicate (approximate)
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]
        
        if distances and distances[0] < 0.5: # Extremely similar
            # Merge / Upsert
            duplicate_id = ids[0]
            logger.info(f"Deduplication triggered. Updating existing memory {duplicate_id}")
            collection.upsert(
                documents=[text],
                metadatas=[{"importance": score, "timestamp": time.time(), "merged": True}],
                ids=[duplicate_id]
            )
            return True
            
        # 4. Insert new
        new_id = str(uuid.uuid4())
        collection.add(
            documents=[text],
            metadatas=[{"importance": score, "timestamp": time.time(), "merged": False}],
            ids=[new_id]
        )
        logger.info(f"Stored new memory in {collection_name} (Score: {score}/10)")
        return True

engine = CognitiveEngine()
