"""
Narrative generation module for the Automated Insight Engine.

This module sends insights to an LLM (Google Gemini or OpenAI) with a
structured JSON prompt and receives narrative content for the report.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import get_narrative_logger

logger = get_narrative_logger()

# Gemini import with fallback
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI SDK not installed.")

# OpenAI import with fallback
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not installed.")


@dataclass
class NarrativeSection:
    """
    Structured narrative section from LLM response.
    
    Attributes:
        title: Section title
        headline: Main headline summarizing key finding
        bullets: List of bullet points with details
        recommendation: Actionable recommendation
    """
    title: str
    headline: str
    bullets: List[str]
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# LLM prompt template - MUST follow this exact JSON schema
LLM_PROMPT_TEMPLATE = """You are an expert marketing analyst. Analyze the following performance insights and generate a structured narrative.

INSIGHT DATA:
{insight_json}

CONTEXT:
- Comparing period: {current_period} vs {previous_period}
- Key dimensions: {dimensions}
- Priority KPIs: {kpis}

Return ONLY this JSON schema:
{{
  "title": "",
  "headline": "",
  "bullets": ["", "", ""],
  "recommendation": ""
}}
No markdown. No explanations. Valid JSON only.

Guidelines:
- title: A brief descriptive title for the report section
- headline: One impactful sentence summarizing the most important finding
- bullets: Exactly 3 bullet points highlighting key changes with specific numbers
- recommendation: One actionable recommendation based on the insights"""


def build_llm_prompt(insights_data: Dict[str, Any]) -> str:
    """
    Build the LLM prompt from insights data.
    
    Args:
        insights_data: Dictionary containing insights and config
        
    Returns:
        Formatted prompt string
    """
    # Extract top insights for context (limit to top 10)
    top_insights = insights_data.get("insights", [])[:10]
    config = insights_data.get("config", {})
    
    # Format insight JSON
    insight_json = json.dumps(top_insights, indent=2)
    
    prompt = LLM_PROMPT_TEMPLATE.format(
        insight_json=insight_json,
        current_period=config.get("current_period", "N/A"),
        previous_period=config.get("previous_period", "N/A"),
        dimensions=", ".join(config.get("dimensions", [])),
        kpis=", ".join(config.get("kpis", []))
    )
    
    return prompt


def call_openai(
    prompt: str,
    api_key: str,
    model: str = "gpt-4.1-mini"
) -> str:
    """
    Call OpenAI API with the given prompt.
    
    Args:
        prompt: The prompt to send
        api_key: OpenAI API key
        model: Model name to use
        
    Returns:
        Raw response content from the model
        
    Raises:
        Exception: If API call fails
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI SDK not installed")
    
    if not api_key:
        raise ValueError("OpenAI API key not provided")
    
    logger.info(f"Calling OpenAI API with model: {model}")
    
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a data analyst assistant that returns only valid JSON responses."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,  # Lower temperature for more consistent JSON output
        max_tokens=1000
    )
    
    content = response.choices[0].message.content
    logger.debug(f"OpenAI response: {content[:200]}...")
    
    return content


def call_gemini(
    prompt: str,
    api_key: str,
    model: str = "gemini-2.0-flash"
) -> str:
    """
    Call Google Gemini API with the given prompt.
    
    Args:
        prompt: The prompt to send
        api_key: Gemini API key
        model: Model name to use
        
    Returns:
        Raw response content from the model
        
    Raises:
        Exception: If API call fails
    """
    if not GEMINI_AVAILABLE:
        raise ImportError("Google Generative AI SDK not installed")
    
    if not api_key:
        raise ValueError("Gemini API key not provided")
    
    logger.info(f"Calling Gemini API with model: {model}")
    
    # Configure the API
    genai.configure(api_key=api_key)
    
    # Create the model
    gemini_model = genai.GenerativeModel(model)
    
    # Generate response
    response = gemini_model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=1000,
        )
    )
    
    content = response.text
    logger.debug(f"Gemini response: {content[:200]}...")
    
    return content


def parse_llm_response(response: str) -> NarrativeSection:
    """
    Parse LLM response JSON into NarrativeSection.
    
    Args:
        response: Raw response string from LLM
        
    Returns:
        NarrativeSection object
        
    Raises:
        ValueError: If response cannot be parsed
    """
    # Clean response (remove markdown code blocks if present)
    cleaned = response.strip()
    if cleaned.startswith("```"):
        # Remove code block markers
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError(f"Invalid JSON response from LLM: {e}")
    
    # Validate required fields
    required_fields = ["title", "headline", "bullets", "recommendation"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields in LLM response: {missing}")
    
    # Ensure bullets is a list
    if not isinstance(data["bullets"], list):
        data["bullets"] = [str(data["bullets"])]
    
    return NarrativeSection(
        title=str(data["title"]),
        headline=str(data["headline"]),
        bullets=[str(b) for b in data["bullets"]],
        recommendation=str(data["recommendation"])
    )


def generate_fallback_narrative(insights_data: Dict[str, Any]) -> NarrativeSection:
    """
    Generate a fallback narrative without LLM when API is unavailable.
    
    Args:
        insights_data: Dictionary containing insights and config
        
    Returns:
        NarrativeSection with auto-generated content
    """
    logger.info("Generating fallback narrative (no LLM)")
    
    insights = insights_data.get("insights", [])
    summary = insights_data.get("summary", {})
    config = insights_data.get("config", {})
    
    # Build title
    title = "Performance Analysis Report"
    
    # Build headline from top mover
    top_mover = summary.get("top_mover")
    if top_mover:
        direction = "increased" if top_mover["direction"] == "up" else "decreased"
        headline = (
            f"Key Finding: {top_mover['metric'].upper()} {direction} by "
            f"{abs(top_mover['delta_pct']):.1f}% in the current period."
        )
    else:
        headline = "Performance metrics remained stable across the analysis period."
    
    # Build bullets from top insights
    bullets = []
    for i, insight in enumerate(insights[:3]):
        dims = insight.get("dimensions", {})
        dim_str = ", ".join(f"{k}={v}" for k, v in dims.items()) if dims else "Overall"
        direction = "up" if insight["direction"] == "up" else "down"
        
        bullet = (
            f"{insight['metric'].upper()} for {dim_str}: "
            f"{insight['current_value']:,.2f} → {insight['previous_value']:,.2f} "
            f"({insight['delta_pct']:+.1f}%)"
        )
        bullets.append(bullet)
    
    # Pad bullets if needed
    while len(bullets) < 3:
        bullets.append("Additional analysis pending.")
    
    # Build recommendation
    if top_mover:
        if top_mover["direction"] == "up":
            recommendation = (
                f"Continue monitoring {top_mover['metric']} performance and identify "
                "factors contributing to the positive trend."
            )
        else:
            recommendation = (
                f"Investigate the decline in {top_mover['metric']} and implement "
                "corrective measures to reverse the trend."
            )
    else:
        recommendation = "Continue monitoring key metrics for emerging trends."
    
    return NarrativeSection(
        title=title,
        headline=headline,
        bullets=bullets,
        recommendation=recommendation
    )


def generate_narrative(
    insights_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    provider: str = "auto"
) -> NarrativeSection:
    """
    Main entry point for narrative generation.
    
    This function sends insights to the LLM and returns a structured
    narrative section. Falls back to auto-generated content if LLM
    is unavailable.
    
    Args:
        insights_data: Dictionary containing insights and config
        api_key: API key (optional, uses env var if not provided)
        model: Model name to use
        provider: LLM provider - "gemini", "openai", or "auto" (auto-detect)
        
    Returns:
        NarrativeSection with title, headline, bullets, and recommendation
    """
    logger.info("Starting narrative generation")
    
    # Get API keys from parameters or environment
    gemini_key = api_key if api_key and api_key.startswith("AIza") else os.getenv("GEMINI_API_KEY", "")
    openai_key = api_key if api_key and api_key.startswith("sk-") else os.getenv("OPENAI_API_KEY", "")
    
    # Auto-detect provider based on available keys and SDKs
    if provider == "auto":
        if gemini_key and GEMINI_AVAILABLE:
            provider = "gemini"
        elif openai_key and OPENAI_AVAILABLE:
            provider = "openai"
        else:
            provider = None
    
    if not provider:
        logger.warning("No LLM provider available, using fallback narrative generation")
        return generate_fallback_narrative(insights_data)
    
    try:
        # Build prompt
        prompt = build_llm_prompt(insights_data)
        logger.debug(f"LLM Prompt length: {len(prompt)} chars")
        
        # Call appropriate LLM
        if provider == "gemini":
            response = call_gemini(prompt, gemini_key, model if "gemini" in model else "gemini-2.0-flash")
        elif provider == "openai":
            response = call_openai(prompt, openai_key, model if "gpt" in model else "gpt-4.1-mini")
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Parse response
        narrative = parse_llm_response(response)
        logger.info(f"Successfully generated narrative from {provider}")
        
        return narrative
        
    except Exception as e:
        logger.error(f"LLM narrative generation failed: {e}")
        logger.info("Falling back to auto-generated narrative")
        return generate_fallback_narrative(insights_data)
