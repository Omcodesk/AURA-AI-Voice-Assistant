"""
actions/weather_service.py — Fetches weather using Open-Meteo (no API key).
"""
import urllib.request
import json
import urllib.parse
from loguru import logger

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry
from core.config_loader import config

from datetime import datetime

def handle_weather(cmd: ParsedCommand) -> ExecutionResult:
    # Phase 4: Priority Location Resolution
    # 1. Check arguments['location'] (from slot_extractor)
    # 2. Check cmd.target (legacy/fallback)
    # 3. Default to Dehradun
    extracted_loc = cmd.arguments.get("location") or cmd.target
    is_fallback = False
    
    if not extracted_loc or extracted_loc.strip() == "":
        location = "Dehradun"
        is_fallback = True
    else:
        location = extracted_loc.strip()
        
    logger.info("Weather Service Attempt | Raw: '{}' | Extracted: '{}'", cmd.source_text, extracted_loc)
    logger.info("Weather Service Resolve | Target: '{}' | Source: '{}'", 
                location, "Default Fallback" if is_fallback else "User Speech")
    
    try:
        # 1. Geocode city
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
        with urllib.request.urlopen(geo_url) as response:
            data = json.loads(response.read().decode())
            
        if not data.get("results"):
            logger.warning("Weather Service Status | Failed | Geocoding failed for: '{}'", location)
            return ExecutionResult(False, f"I couldn't find the location {location} on the map.")
            
        lat = data["results"][0]["latitude"]
        lon = data["results"][0]["longitude"]
        city = data["results"][0]["name"]
        country = data.get("results", [{}])[0].get("country", "")
        
        # 2. Get Weather with advanced fields
        # Requesting: temperature_2m, relative_humidity_2m, wind_speed_10m, weather_code
        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
               f"&temperature_unit=celsius&wind_speed_unit=kmh&timezone=auto")
        
        logger.debug("Executing weather lookup target: '{}' ({}, {})", city, lat, lon)
        with urllib.request.urlopen(url) as response:
            w_data = json.loads(response.read().decode())
            
        current = w_data["current"]
        temp = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind_speed = current["wind_speed_10m"]
        raw_time = current["time"] # e.g. "2026-04-15T00:30"
        
        # Parse ISO time to user-friendly format (e.g. 12:30 AM)
        try:
            dt_obj = datetime.fromisoformat(raw_time)
            spoken_time = dt_obj.strftime("%I:%M %p")
        except:
            spoken_time = raw_time # fallback to raw if parsing fails
            
        # Format the precise spoken response
        spoken = (f"As of {spoken_time}, the weather in {city} is {temp} degrees Celsius, "
                  f"humidity is {humidity} percent, and wind speed is {wind_speed} kilometers per hour.")
        
        # Comprehensive Logging
        logger.info("Weather Service Status | Success")
        logger.info("  - Location   : {} ({})", city, country)
        logger.info("  - Coordinates: {}, {}", lat, lon)
        logger.info("  - Source Time: {}", raw_time)
        logger.info("  - Temperature: {} C", temp)
        logger.info("  - Humidity   : {}%", humidity)
        logger.info("  - Wind Speed : {} km/h", wind_speed)
        logger.info("  - Spoken     : '{}'", spoken)
        
        return ExecutionResult(True, spoken, {
            "temp": temp, 
            "humidity": humidity, 
            "wind_speed": wind_speed, 
            "city": city, 
            "time": raw_time
        })
        
    except Exception as exc:
        logger.error("Weather Service Status | Failed | Error: {}", exc)
        return ExecutionResult(False, "I'm sorry, I couldn't reach the weather service right now.")

registry.register("weather", "current_weather", handle_weather)
