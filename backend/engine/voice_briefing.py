"""
Voice Briefing Module.

This module generates audio summaries of insights using text-to-speech.
Supports Murf AI for high-quality voice synthesis and falls back to 
browser-based TTS if API is unavailable.
"""

import os
import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from core.logger import get_logger

logger = get_logger("voice_briefing")

# Murf AI API configuration
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"


def generate_briefing_text(
    narrative: Dict[str, Any],
    insights: list,
    max_length: int = 1500
) -> str:
    """
    Generate a concise text briefing from narrative and insights.
    
    Args:
        narrative: Narrative dictionary with title, summary, highlights
        insights: List of insight dictionaries
        max_length: Maximum character length for briefing
        
    Returns:
        Text suitable for text-to-speech conversion
    """
    parts = []
    
    # Title
    title = narrative.get("title", "Insight Report")
    parts.append(f"Welcome to your {title} briefing.")
    
    # Summary
    summary = narrative.get("summary", "")
    if summary:
        parts.append(summary)
    
    # Key findings
    highlights = narrative.get("highlights", [])
    if highlights:
        parts.append("Here are the key findings:")
        for i, highlight in enumerate(highlights[:3], 1):
            parts.append(f"Finding {i}: {highlight}")
    
    # Top insights
    if insights:
        parts.append("Notable changes include:")
        for insight in insights[:3]:
            metric = insight.get("metric", "Unknown")
            change = insight.get("change", 0)
            direction = "increased" if change > 0 else "decreased"
            abs_change = abs(change)
            parts.append(f"{metric} {direction} by {abs_change:.1f} percent.")
    
    # Recommendation
    recommendation = narrative.get("recommendation", "")
    if recommendation:
        parts.append(f"Recommendation: {recommendation}")
    
    # Closing
    parts.append("End of briefing. Scan the QR code for full details.")
    
    # Join and truncate
    text = " ".join(parts)
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text


def generate_audio_murf(
    text: str,
    api_key: str,
    output_path: str,
    voice_id: str = "en-US-natalie",
    style: str = "Conversational",
    speed: float = 1.0
) -> Tuple[bool, str]:
    """
    Generate audio using Murf AI API.
    
    Args:
        text: Text to convert to speech
        api_key: Murf AI API key
        output_path: Path to save the audio file
        voice_id: Murf voice ID (default: en-US-natalie)
        style: Voice style (Conversational, Newscast, etc.)
        speed: Speech speed multiplier
        
    Returns:
        Tuple of (success, message or error)
    """
    if not api_key:
        return False, "No Murf API key provided"
    
    logger.info(f"Generating audio with Murf AI voice: {voice_id}")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    payload = {
        "voiceId": voice_id,
        "style": style,
        "text": text,
        "rate": int(speed * 100),
        "pitch": 0,
        "sampleRate": 24000,
        "format": "MP3",
        "channelType": "MONO",
        "pronunciationDictionary": {},
        "encodeAsBase64": False,
        "variation": 1,
        "audioDuration": 0,
        "modelVersion": "GEN2"
    }
    
    try:
        response = requests.post(
            MURF_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            audio_url = result.get("audioFile")
            
            if audio_url:
                # Download the audio file
                audio_response = requests.get(audio_url, timeout=30)
                if audio_response.status_code == 200:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(audio_response.content)
                    logger.info(f"Audio saved to: {output_path}")
                    return True, output_path
                else:
                    return False, f"Failed to download audio: {audio_response.status_code}"
            else:
                return False, "No audio URL in response"
        else:
            error_msg = response.text[:200] if response.text else str(response.status_code)
            logger.error(f"Murf API error: {error_msg}")
            return False, f"Murf API error: {error_msg}"
            
    except requests.exceptions.Timeout:
        return False, "Murf API request timed out"
    except requests.exceptions.RequestException as e:
        return False, f"Murf API request failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def generate_briefing_script(
    narrative: Dict[str, Any],
    insights: list
) -> Dict[str, Any]:
    """
    Generate a structured briefing script for browser-based TTS.
    
    This is used as a fallback when Murf AI is not available.
    The frontend can use Web Speech API to read this script.
    
    Args:
        narrative: Narrative dictionary
        insights: List of insights
        
    Returns:
        Structured script with segments and timings
    """
    segments = []
    
    # Opening
    title = narrative.get("title", "Insight Report")
    segments.append({
        "type": "opening",
        "text": f"Welcome to your {title} briefing.",
        "pause_after": 500
    })
    
    # Summary
    summary = narrative.get("summary", "")
    if summary:
        segments.append({
            "type": "summary",
            "text": summary,
            "pause_after": 800
        })
    
    # Highlights
    highlights = narrative.get("highlights", [])
    if highlights:
        segments.append({
            "type": "section_header",
            "text": "Key findings:",
            "pause_after": 400
        })
        for highlight in highlights[:3]:
            segments.append({
                "type": "highlight",
                "text": highlight,
                "pause_after": 600
            })
    
    # Insights
    if insights:
        segments.append({
            "type": "section_header",
            "text": "Notable changes:",
            "pause_after": 400
        })
        for insight in insights[:3]:
            metric = insight.get("metric", "Unknown")
            change = insight.get("change", 0)
            direction = "increased" if change > 0 else "decreased"
            abs_change = abs(change)
            segments.append({
                "type": "insight",
                "text": f"{metric} {direction} by {abs_change:.1f} percent.",
                "pause_after": 500
            })
    
    # Recommendation
    recommendation = narrative.get("recommendation", "")
    if recommendation:
        segments.append({
            "type": "recommendation",
            "text": f"Recommendation: {recommendation}",
            "pause_after": 800
        })
    
    # Closing
    segments.append({
        "type": "closing",
        "text": "End of briefing.",
        "pause_after": 0
    })
    
    return {
        "segments": segments,
        "total_segments": len(segments),
        "full_text": generate_briefing_text(narrative, insights)
    }


def generate_voice_briefing(
    narrative: Dict[str, Any],
    insights: list,
    output_dir: str,
    session_id: str,
    murf_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a voice briefing for the dashboard.
    
    Attempts to use Murf AI first, falls back to browser TTS script.
    
    Args:
        narrative: Narrative dictionary
        insights: List of insights
        output_dir: Directory to save audio files
        session_id: Session identifier for filename
        murf_api_key: Optional Murf AI API key
        
    Returns:
        Dictionary with audio_url or tts_script for playback
    """
    logger.info(f"Generating voice briefing for session: {session_id}")
    
    # Generate briefing text
    text = generate_briefing_text(narrative, insights)
    
    result = {
        "session_id": session_id,
        "generated_at": datetime.now().isoformat(),
        "text_length": len(text)
    }
    
    # Try Murf AI if API key is available
    if murf_api_key:
        output_path = str(Path(output_dir) / f"briefing_{session_id}.mp3")
        success, message = generate_audio_murf(
            text=text,
            api_key=murf_api_key,
            output_path=output_path
        )
        
        if success:
            result["audio_type"] = "murf"
            result["audio_path"] = output_path
            result["audio_url"] = f"/static/audio/briefing_{session_id}.mp3"
            logger.info("Murf AI audio generated successfully")
            return result
        else:
            logger.warning(f"Murf AI failed: {message}, falling back to browser TTS")
    
    # Fallback to browser TTS script
    result["audio_type"] = "browser_tts"
    result["tts_script"] = generate_briefing_script(narrative, insights)
    result["audio_url"] = None
    logger.info("Generated browser TTS script")
    
    return result


# Test function
if __name__ == "__main__":
    print("Testing Voice Briefing Module...")
    
    # Sample data
    narrative = {
        "title": "Marketing Campaign Analysis",
        "summary": "Overall performance remained stable with minor fluctuations.",
        "highlights": [
            "Wine sales increased by 12%",
            "Web visits decreased slightly",
            "Customer retention improved"
        ],
        "recommendation": "Focus on digital marketing to boost web engagement."
    }
    
    insights = [
        {"metric": "MntWines", "change": 12.5, "impact": 0.8},
        {"metric": "NumWebVisits", "change": -3.2, "impact": 0.5},
        {"metric": "Response", "change": 8.0, "impact": 0.7}
    ]
    
    # Test text generation
    text = generate_briefing_text(narrative, insights)
    print(f"Generated text ({len(text)} chars):")
    print(text[:500])
    print()
    
    # Test script generation
    script = generate_briefing_script(narrative, insights)
    print(f"Generated script with {script['total_segments']} segments")
    
    print("\nVoice Briefing Module test complete!")
