import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brain.intent_router import router
from loguru import logger

# Disable detailed logs for clean output
logger.remove()
logger.add(sys.stderr, level="INFO")

def test_phrases():
    phrases = [
        # Exact phrases
        "open browser",
        "open chrome",
        "take a screenshot",
        
        # Polite phrases
        "can you open browser",
        "could you please take a screenshot",
        
        # Typo/Noisy phrases
        "opne browser",
        "open chrrome",
        "search for this on browser",
        
        # Site mapping
        "open youtube",
        "go to gmail",
        
        # Context phrases (requires some setup in memory usually)
        "open it",
        
        # Multi-step
        "open edge and go to youtube",
        "take a screenshot and open it"
    ]
    
    print("\n" + "="*50)
    print("UNIVERSAL INTENT BRAIN - VARIATION TESTS")
    print("="*50 + "\n")
    
    for p in phrases:
        print(f"INPUT:  '{p}'")
        res = router.route(p)
        
        for i, cmd in enumerate(res):
            print(f"RESULT {i+1}: Intent={cmd.intent}, Action={cmd.action}, Target='{cmd.target}'")
        print("-" * 30)

if __name__ == "__main__":
    test_phrases()
