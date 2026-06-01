"""
services/memory/chroma_client.py — ChromaDB Client Singleton
"""
import os
import chromadb
from loguru import logger
from core.config_loader import config

class ChromaMemoryClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaMemoryClient, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance
        
    def _init_db(self):
        # Store ChromaDB in the local data directory
        db_path = os.path.join(os.getcwd(), "data", "chroma_db")
        os.makedirs(db_path, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(path=db_path)
            # Pre-initialize core collections
            self.get_collection("aura_episodic")
            self.get_collection("aura_semantic")
            self.get_collection("aura_procedural")
            logger.info(f"ChromaDB initialized at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            
    def get_collection(self, name: str):
        if not self.client:
            return None
        return self.client.get_or_create_collection(name=name)

# Singleton instance
memory_db = ChromaMemoryClient()
