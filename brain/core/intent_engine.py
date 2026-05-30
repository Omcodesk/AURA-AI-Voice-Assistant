from loguru import logger
from brain.core.command_normalizer import normalizer
from brain.core.context_memory import context_memory
from brain.core.slot_extractor import slot_extractor
from brain.core.fast_rule_matcher import matcher
from brain.core.llm_intent_brain import llm_brain
from brain.core.multi_intent_parser import multi_parser
from brain.core.confidence_guard import confidence_guard

class IntentEngine:
    def process(self, text: str) -> list[dict]:
        """
        Main pipeline (Single-Intent Optimized):
        1. Normalize text
        2. Fast Match -> fallback to LLM
        3. Extract slots & resolve context
        4. Guard & Return
        """
        clean_text = normalizer.normalize(text)
        logger.info("Processing intent: '{}' (normalized: '{}')", text, clean_text)
        
        # A. Try Fast Match (Deterministic - First & Fastest)
        intent = matcher.match(clean_text)
        if intent:
            res = {
                "intent": intent,
                "action": intent,
                "slots": slot_extractor.extract_slots(intent, clean_text),
                "confidence": 1.0,
                "needs_clarification": False,
                "requires_confirmation": False
            }
        else:
            # B. Try LLM Fallback (Reasoning - Second)
            ctx = context_memory.get_last() or ""
            res = llm_brain.classify(clean_text, context=ctx)
            if not res:
                # Final fallback to conversation
                res = {
                    "intent": "conversation",
                    "action": "chat",
                    "slots": {"text": clean_text},
                    "confidence": 0.5
                }
            
        # C. Context Resolution (it, this, that)
        for key, val in res.get("slots", {}).items():
            if val in ("it", "this", "that"):
                resolved = context_memory.resolve(val)
                if resolved:
                    res["slots"][key] = resolved["value"]
                    logger.info("Resolved '{}' to '{}'", val, resolved["value"])

        # D. Canonical Cross-Check
        # If 'open_app' targets a known site, pivot to 'open_website'
        if res["intent"] == "open_app" and "app" in res["slots"]:
            site_url = slot_extractor._canonical_site(res["slots"]["app"])
            if site_url:
                res["intent"] = "open_website"
                res["action"] = "open_website"
                res["slots"] = {"url": site_url, "site": res["slots"]["app"]}
                logger.info("Pivoted open_app -> open_website for '{}'", site_url)

        # E. Confidence Guard
        res = confidence_guard.evaluate(res)
            
        # F. Update Context Memory
        if res.get("intent") != "conversation":
             # Extract the most important entity for next turn
             for s_key in ("app", "site", "url", "target", "query", "location"):
                 if s_key in res["slots"]:
                     context_memory.update(s_key, res["slots"][s_key])
                     break
        
        return [res]

engine = IntentEngine()
