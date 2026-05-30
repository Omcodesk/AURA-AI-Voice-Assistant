from loguru import logger

class ConfidenceGuard:
    def __init__(self, threshold=0.6):
        self.threshold = threshold

    def evaluate(self, result: dict) -> dict:
        """
        Gaurds execution by checking confidence and destructive risk.
        """
        confidence = result.get("confidence", 1.0) # Rules are 1.0
        intent = result.get("intent", "conversation")
        
        if confidence < self.threshold:
            result["needs_clarification"] = True
            result["clarification_question"] = "I'm not sure what you mean. Could you say that differently?"
            
        # Hard limits for risky intents if confidence isn't perfect
        if intent in ("system_control", "email", "whatsapp") and confidence < 0.9:
             result["requires_confirmation"] = True
             
        return result

confidence_guard = ConfidenceGuard()
