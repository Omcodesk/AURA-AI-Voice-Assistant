"""
test_reminders.py — Unit tests for the TimeParser and Reminder logic.
"""
from datetime import datetime, timedelta
from brain.core.time_parser import time_parser

def test_relative():
    now = datetime.now()
    # Test "in 10 minutes"
    target = time_parser.parse("in 10 minutes")
    diff = (target - now).total_seconds()
    assert 595 < diff < 605
    print("Relative 'in 10 minutes' test passed.")

    # Test "in 1 hour"
    target = time_parser.parse("in 1 hr")
    diff = (target - now).total_seconds()
    assert 3595 < diff < 3605
    print("Relative 'in 1 hour' test passed.")

def test_absolute():
    now = datetime.now()
    # Test "at 7 pm" 
    target = time_parser.parse("at 7 pm")
    assert target.hour == 19
    assert target.minute == 0
    # verify tomorrow rollover
    if now.hour >= 19:
        assert target.day == (now + timedelta(days=1)).day
    print("Absolute 'at 7 pm' test passed.")
    
    # Test "at 8:30"
    target = time_parser.parse("at 8:30")
    assert target.hour == 8
    assert target.minute == 30
    print("Absolute 'at 8:30' test passed.")

if __name__ == "__main__":
    test_relative()
    test_absolute()
    print("\nAll TimeParser tests passed locally.")
