"""
actions/reminders.py — Service logic for setting and managing alarms/reminders.
"""

from loguru import logger
from datetime import datetime

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry
from brain.memory_manager import memory
from brain.core.time_parser import time_parser

def handle_set_reminder(cmd: ParsedCommand) -> ExecutionResult:
    task = cmd.arguments.get("task", "something")
    time_str = cmd.arguments.get("time", "")
    
    if not time_str:
        return ExecutionResult(False, "I didn't hear a specific time for the reminder. When should I remind you?")

    target_dt = time_parser.parse(time_str)
    if not target_dt:
        return ExecutionResult(False, f"I couldn't understand the time '{time_str}'. Please try saying it differently.")

    rid = memory.add_reminder(task, target_dt, rtype="reminder")
    time_display = target_dt.strftime("%I:%M %p")
    
    msg = f"Okay, I'll remind you to {task} at {time_display}."
    logger.info("Reminder Scheduled [ID:{}]: '{}' at {}", rid, task, target_dt)
    return ExecutionResult(True, msg)

def handle_set_alarm(cmd: ParsedCommand) -> ExecutionResult:
    time_str = cmd.arguments.get("time", "")
    
    if not time_str:
        return ExecutionResult(False, "When should I set the alarm for?")

    target_dt = time_parser.parse(time_str)
    if not target_dt:
        return ExecutionResult(False, f"I couldn't understand the time '{time_str}'.")

    rid = memory.add_reminder("Alarm", target_dt, rtype="alarm")
    time_display = target_dt.strftime("%I:%M %p")
    
    msg = f"Alarm set for {time_display}."
    logger.info("Alarm Scheduled [ID:{}]: at {}", rid, target_dt)
    return ExecutionResult(True, msg)

def handle_cancel_reminder(cmd: ParsedCommand) -> ExecutionResult:
    # For now, we'll cancel the most recently added incomplete reminder/alarm
    # In a more advanced version, we could match by message
    due = memory.get_due_reminders()
    # Or just fetch all incomplete
    from sqlmodel import Session, select
    from brain.memory_manager import Reminder
    
    with Session(memory._engine) as s:
        stmt = select(Reminder).where(Reminder.completed == False).order_by(Reminder.created_at.desc())
        rem = s.exec(stmt).first()
        if rem:
            rtype = rem.type
            memory.delete_reminder(rem.id)
            return ExecutionResult(True, f"Okay, I've cancelled your {rtype}.")
            
    return ExecutionResult(False, "You don't have any active alarms or reminders to cancel.")

SNOOZE_MINUTES = 5 # Configurable

def handle_snooze(cmd: ParsedCommand) -> ExecutionResult:
    # 1. Get the most recently completed reminder (the one that just fired)
    from sqlmodel import Session, select, desc
    from brain.memory_manager import Reminder
    
    with Session(memory._engine) as s:
        stmt = select(Reminder).where(Reminder.completed == True).order_by(desc(Reminder.remind_at))
        last_rem = s.exec(stmt).first()
        
        if not last_rem:
            return ExecutionResult(False, "There is nothing to snooze.")
            
        # 2. Reschedule it
        new_time = datetime.now() + timedelta(minutes=SNOOZE_MINUTES)
        memory.add_reminder(last_rem.message, new_time, rtype=last_rem.type)
        
        logger.info("Snoozed reminder [Prev ID:{}] for {} minutes", last_rem.id, SNOOZE_MINUTES)
        return ExecutionResult(True, f"Okay, snoozing for {SNOOZE_MINUTES} minutes.")

# Register intents
registry.register("set_reminder", "set_reminder", handle_set_reminder)
registry.register("set_alarm", "set_alarm", handle_set_alarm)
registry.register("cancel_reminder", "cancel", handle_cancel_reminder)
registry.register("snooze", "snooze", handle_snooze)
