"""
auth/user_registry.py — Persistent user store: names + face embeddings in SQLite.
Embeddings are stored as numpy blobs. Cosine similarity used for matching.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from datetime import datetime

from sqlmodel import Field, Session, SQLModel, create_engine, select
from loguru import logger
from core.config_loader import config


# ── Schema ────────────────────────────────────────────────────────────────────

class EnrolledUser(SQLModel, table=True):
    id: Optional[int]        = Field(default=None, primary_key=True)
    name: str                = Field(index=True)
    authorized: bool         = Field(default=True)
    embedding_blob: bytes    = Field()            # numpy float32 array as bytes
    enrolled_at: datetime    = Field(default_factory=datetime.now)
    last_seen: Optional[datetime] = Field(default=None)


# ── Registry ──────────────────────────────────────────────────────────────────

class UserRegistry:
    _instance: UserRegistry | None = None

    def __new__(cls) -> UserRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine = None
        return cls._instance

    def init_db(self) -> None:
        db_path = Path(config.get("memory.database_path", "data/memory/aura.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        SQLModel.metadata.create_all(self._engine)
        
        # Migrate enrolled users from jarvis.db if aura.db is empty
        try:
            if self.is_empty():
                old_db_path = db_path.parent / "jarvis.db"
                if old_db_path.exists():
                    logger.info("Migrating enrolled users from jarvis.db to aura.db...")
                    old_engine = create_engine(f"sqlite:///{old_db_path}", echo=False)
                    with Session(old_engine) as old_sess, Session(self._engine) as new_sess:
                        from sqlalchemy import text
                        users = old_sess.execute(text("SELECT name, authorized, embedding_blob, enrolled_at, last_seen FROM enrolleduser")).fetchall()
                        for u in users:
                            new_sess.execute(
                                text("INSERT INTO enrolleduser (name, authorized, embedding_blob, enrolled_at, last_seen) VALUES (:name, :authorized, :embedding_blob, :enrolled_at, :last_seen)"),
                                {
                                    "name": u[0],
                                    "authorized": u[1],
                                    "embedding_blob": u[2],
                                    "enrolled_at": u[3],
                                    "last_seen": u[4]
                                }
                            )
                        new_sess.commit()
                        logger.info("Successfully migrated {} users from jarvis.db to aura.db", len(users))
        except Exception as e:
            logger.warning("Failed to migrate enrolled users: {}", e)
            
        logger.info("UserRegistry ready — {} users enrolled", self.count())

    # ── Write ─────────────────────────────────────────────────────────────────

    def enroll(self, name: str, embedding: np.ndarray, authorized: bool = True) -> int:
        blob = embedding.astype(np.float32).tobytes()
        with Session(self._engine) as s:
            user = EnrolledUser(name=name, authorized=authorized, embedding_blob=blob)
            s.add(user)
            s.commit()
            s.refresh(user)
            logger.info("Enrolled user '{}' (id={})", name, user.id)
            return user.id

    def update_last_seen(self, user_id: int) -> None:
        with Session(self._engine) as s:
            user = s.get(EnrolledUser, user_id)
            if user:
                user.last_seen = datetime.now()
                s.add(user)
                s.commit()

    def set_authorized(self, user_id: int, authorized: bool) -> None:
        with Session(self._engine) as s:
            user = s.get(EnrolledUser, user_id)
            if user:
                user.authorized = authorized
                s.add(user)
                s.commit()

    def delete_user(self, user_id: int) -> None:
        with Session(self._engine) as s:
            user = s.get(EnrolledUser, user_id)
            if user:
                s.delete(user)
                s.commit()
                logger.info("Deleted user id={}", user_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        with Session(self._engine) as s:
            users = list(s.exec(select(EnrolledUser)).all())
            return [
                {
                    "id": u.id,
                    "name": u.name,
                    "authorized": u.authorized,
                    "embedding": np.frombuffer(u.embedding_blob, dtype=np.float32),
                    "enrolled_at": u.enrolled_at,
                    "last_seen": u.last_seen,
                }
                for u in users
            ]

    def count(self) -> int:
        with Session(self._engine) as s:
            return len(list(s.exec(select(EnrolledUser)).all()))

    def is_empty(self) -> bool:
        return self.count() == 0

    # ── Matching ──────────────────────────────────────────────────────────────

    def match(self, embedding: np.ndarray, threshold: float = 0.35) -> dict | None:
        """
        Cosine-similarity match against all enrolled users.
        Returns the best match dict (with 'similarity' key) or None.
        """
        users = self.get_all()
        if not users:
            return None

        emb = embedding / (np.linalg.norm(embedding) + 1e-9)
        best_score = -1.0
        best_user = None

        for u in users:
            stored = u["embedding"] / (np.linalg.norm(u["embedding"]) + 1e-9)
            score = float(np.dot(emb, stored))
            if score > best_score:
                best_score = score
                best_user = u

        if best_score >= threshold and best_user is not None:
            best_user["similarity"] = best_score
            return best_user

        return None


# Module-level singleton
registry = UserRegistry()
