"""
brain/memory_manager.py — SQLite-backed user preference, routine, and alias memory.
Uses sqlmodel for schema definition and SQLite for storage.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select
from loguru import logger
from core.config_loader import config


# ── SQLModel tables ─────────────────────────────────────────────────────────

class Preference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str
    updated_at: datetime = Field(default_factory=datetime.now)


class CommandAlias(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phrase: str = Field(index=True, unique=True)
    intent: str
    use_count: int = Field(default=1)
    last_used: datetime = Field(default_factory=datetime.now)


class ConversationTurn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_text: str
    aura_text: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message: str
    remind_at: datetime
    type: str = Field(default="reminder") # "alarm" or "reminder"
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


# ── Manager ─────────────────────────────────────────────────────────────────

class MemoryManager:
    _instance: MemoryManager | None = None

    def __new__(cls) -> MemoryManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine = None
        return cls._instance

    def init_db(self) -> None:
        db_path = Path(config.get("memory.database_path", "data/memory/jarvis.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        SQLModel.metadata.create_all(self._engine)
        
        # Self-healing migration for existing databases
        from sqlalchemy import text
        try:
            with self._engine.begin() as conn:
                res = conn.execute(text("PRAGMA table_info(reminder)")).fetchall()
                if res:
                    columns = [r[1] for r in res]
                    if "type" not in columns:
                        logger.info("Migrating database: Adding 'type' column to 'reminder' table.")
                        conn.execute(text("ALTER TABLE reminder ADD COLUMN type VARCHAR DEFAULT 'reminder'"))
        except Exception as e:
            logger.warning("Database self-healing migration failed: {}", e)
            
        logger.info("MemoryManager DB ready at '{}'", db_path)

    # ── Preferences ─────────────────────────────────────────────────────────

    def set_pref(self, key: str, value: str) -> None:
        with Session(self._engine) as s:
            pref = s.exec(select(Preference).where(Preference.key == key)).first()
            if pref:
                pref.value = value
                pref.updated_at = datetime.now()
            else:
                pref = Preference(key=key, value=value)
            s.add(pref)
            s.commit()

    def get_pref(self, key: str, default: str = "") -> str:
        with Session(self._engine) as s:
            pref = s.exec(select(Preference).where(Preference.key == key)).first()
            return pref.value if pref else default

    # ── Learned aliases ──────────────────────────────────────────────────────

    def record_alias(self, phrase: str, intent: str) -> None:
        with Session(self._engine) as s:
            alias = s.exec(select(CommandAlias).where(CommandAlias.phrase == phrase)).first()
            if alias:
                alias.use_count += 1
                alias.last_used = datetime.now()
            else:
                alias = CommandAlias(phrase=phrase, intent=intent)
            s.add(alias)
            s.commit()

    def get_learned_intent(self, phrase: str, min_uses: int = 3) -> str | None:
        """Return learned intent for a phrase if it has been used enough times."""
        with Session(self._engine) as s:
            alias = s.exec(select(CommandAlias).where(CommandAlias.phrase == phrase)).first()
            if alias and alias.use_count >= min_uses:
                return alias.intent
        return None

    # ── Conversation log ────────────────────────────────────────────────────

    def log_turn(self, user_text: str, aura_text: str) -> None:
        with Session(self._engine) as s:
            turn = ConversationTurn(user_text=user_text, aura_text=aura_text)
            s.add(turn)
            s.commit()

    def recent_turns(self, n: int = 5) -> list[ConversationTurn]:
        with Session(self._engine) as s:
            return list(
                s.exec(
                    select(ConversationTurn)
                    .order_by(ConversationTurn.timestamp.desc())
                    .limit(n)
                ).all()
            )

    # ── Reminders & Alarms ──────────────────────────────────────────────────

    def add_reminder(self, message: str, remind_at: datetime, rtype: str = "reminder") -> int:
        with Session(self._engine) as s:
            rem = Reminder(message=message, remind_at=remind_at, type=rtype)
            s.add(rem)
            s.commit()
            s.refresh(rem)
            return rem.id or 0

    def get_due_reminders(self) -> list[Reminder]:
        """Fetch all reminders that are due and not yet completed."""
        with Session(self._engine) as s:
            now = datetime.now()
            return list(
                s.exec(
                    select(Reminder)
                    .where(Reminder.remind_at <= now)
                    .where(Reminder.completed == False)
                ).all()
            )

    def mark_reminder_completed(self, rid: int) -> None:
        with Session(self._engine) as s:
            rem = s.get(Reminder, rid)
            if rem:
                rem.completed = True
                s.add(rem)
                s.commit()

    def delete_reminder(self, rid: int) -> bool:
        with Session(self._engine) as s:
            rem = s.get(Reminder, rid)
            if rem:
                s.delete(rem)
                s.commit()
                return True
            return False


# Module-level singleton
memory = MemoryManager()
