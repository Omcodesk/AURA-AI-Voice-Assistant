"""
vision/grounding.py — Translates semantic element names to X/Y coordinates using Vision.
"""
import json
import re
from loguru import logger
from vision.vlm_client import vlm_client
import pyautogui

def ground_element(element_name: str) -> tuple[int, int] | None:
    """
    Given a semantic name (e.g. 'Search Bar'), returns the (x, y) screen coordinates.
    Uses the Vision LLM to parse the UI.
    """
    logger.info("Grounding element '{}' to spatial coordinates...", element_name)
    
    # 1. Capture and analyze using Vision
    screen_w, screen_h = pyautogui.size()
    
    prompt = f"""You are an expert UI parsing agent.
The user wants to interact with an element called '{element_name}'.
Look at the screen and find this element. 
Estimate its center coordinates on a screen of size {screen_w}x{screen_h}.
Return ONLY a valid JSON object in this format: {{"x": 500, "y": 300, "found": true}}
If the element is absolutely not visible, return {{"found": false}}.
Do not output any markdown formatting, only raw JSON.
"""
    response = vlm_client.analyze_screen(prompt)
    
    if not response or "Error" in response:
        logger.error("Vision API failed during grounding.")
        return None
        
    # 2. Parse JSON robustly
    try:
        # Strip potential markdown formatting if the LLM ignores instructions
        clean_json = re.sub(r'```(?:json)?|```', '', response).strip()
        data = json.loads(clean_json)
        
        if data.get("found") and "x" in data and "y" in data:
            x, y = int(data["x"]), int(data["y"])
            logger.info("Grounded '{}' to ({}, {})", element_name, x, y)
            return (x, y)
        else:
            logger.warning("Vision model could not find '{}'", element_name)
            return None
    except Exception as e:
        logger.error("Failed to parse VLM grounding response: {}. Response: {}", e, response)
        # Fallback for testing: return center of screen
        return (screen_w // 2, screen_h // 2)

