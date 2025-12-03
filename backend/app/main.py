"""
FastAPI application for the Automated Insight Engine.

This module provides the REST API endpoint for generating reports
from uploaded configuration files.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import tempfile
import shutil

# Load environment variables from .env file
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from pydantic import BaseModel
from typing import Optional

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.config import load_config_from_string, get_app_settings, InsightConfig
from core.logger import setup_logger, get_api_logger
from engine.ingest import ingest_data
from engine.metrics import process_metrics
from engine.insights import generate_insights
from engine.narrative import generate_narrative
from engine.report_pptx import generate_report
from engine.session_manager import get_session_manager, DashboardSession
from engine.voice_briefing import generate_voice_briefing
from engine.qrcode_gen import generate_qr_for_dashboard

# Initialize logger
logger = get_api_logger()
setup_logger("insight_engine", level="INFO")

# Create FastAPI app
app = FastAPI(
    title="Automated Insight Engine",
    description="Generate insightful reports from your data with AI-powered analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Get application settings
settings = get_app_settings()

# Get project root directory (parent of backend)
project_root = Path(__file__).parent.parent.parent

# Set absolute paths for reports and tmp directories
reports_dir = project_root / "static" / "reports"
audio_dir = project_root / "static" / "audio"
tmp_dir = project_root / "tmp"
sessions_dir = tmp_dir / "sessions"

# Ensure directories exist
reports_dir.mkdir(parents=True, exist_ok=True)
audio_dir.mkdir(parents=True, exist_ok=True)
tmp_dir.mkdir(parents=True, exist_ok=True)
sessions_dir.mkdir(parents=True, exist_ok=True)

# Mount static files for report downloads
static_dir = project_root / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount tmp for QR codes
app.mount("/tmp", StaticFiles(directory=str(tmp_dir)), name="tmp")

# Mount frontend
frontend_dir = project_root / "frontend"
app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


class ReportResponse(BaseModel):
    """Response model for report generation."""
    download_url: str
    message: str = "Report generated successfully"
    dashboard_url: Optional[str] = None
    session_id: Optional[str] = None
    audio_url: Optional[str] = None
    voice_script: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str = ""


class ColumnAnalysis(BaseModel):
    """Response model for AI column analysis."""
    date_column: str
    dimensions: list
    metrics: list
    suggested_date_range: dict
    analysis_notes: str


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - serves frontend.
    
    Returns:
        Frontend HTML page
    """
    index_path = project_root / "frontend" / "index.html"
    return FileResponse(str(index_path), media_type="text/html")


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return {"status": "ok"}


def save_uploaded_file(upload_file: UploadFile, dest_dir: str) -> str:
    """
    Save an uploaded file to a temporary location.
    
    Args:
        upload_file: The uploaded file
        dest_dir: Destination directory
        
    Returns:
        Path to the saved file
    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    
    file_path = dest_path / upload_file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return str(file_path)


def get_base_path_from_config(config: InsightConfig, tmp_dir: str) -> str:
    """
    Determine the base path for data files.
    
    If data files are relative paths, returns the parent directory
    where data files should be found.
    
    Args:
        config: Insight configuration
        tmp_dir: Temporary directory where config was saved
        
    Returns:
        Base path for resolving relative data file paths
    """
    # Check if data files use relative paths
    primary_source = config.dataset.sources[config.dataset.primary_source]
    
    if Path(primary_source.path).is_absolute():
        return ""
    
    # For relative paths, check common locations
    possible_bases = [
        Path.cwd(),  # Current working directory
        Path(__file__).parent.parent.parent,  # Project root
        Path(tmp_dir).parent,  # Parent of tmp
    ]
    
    for base in possible_bases:
        test_path = base / primary_source.path
        if test_path.exists():
            return str(base)
    
    # Default to current working directory
    return str(Path.cwd())


@app.post("/analyze-csv", response_model=ColumnAnalysis, tags=["Analysis"])
async def analyze_csv_endpoint(
    csv_file: UploadFile = File(..., description="CSV file to analyze")
) -> ColumnAnalysis:
    """
    Analyze a CSV file using Gemini AI to automatically detect column types.
    
    Returns recommended date column, dimensions, and metrics.
    """
    import json
    import google.generativeai as genai
    
    logger.info(f"Analyzing CSV: {csv_file.filename}")
    
    try:
        # Read CSV content
        content = await csv_file.read()
        text = content.decode('utf-8')
        
        # Parse to get columns and sample data
        lines = text.strip().split('\n')
        
        # Detect delimiter
        first_line = lines[0]
        delimiter = ','
        if first_line.count(';') > first_line.count(','):
            delimiter = ';'
        elif first_line.count('\t') > first_line.count(','):
            delimiter = '\t'
        
        # Get headers and sample rows
        headers = [h.strip().strip('"\'') for h in first_line.split(delimiter)]
        sample_rows = []
        for line in lines[1:6]:  # Get up to 5 sample rows
            row = [v.strip().strip('"\'') for v in line.split(delimiter)]
            if len(row) == len(headers):
                sample_rows.append(dict(zip(headers, row)))
        
        # Build prompt for Gemini
        prompt = f"""Analyze this CSV data and identify the column types for a business analytics report.

COLUMNS: {headers}

SAMPLE DATA (first 5 rows):
{json.dumps(sample_rows, indent=2)}

Based on the column names and sample data, classify each column:

1. DATE COLUMN: Identify THE SINGLE column most likely to contain dates/timestamps for time-series analysis. Look for columns with names like 'date', 'dt_', 'timestamp', 'created_at', etc. or values that look like dates.

2. DIMENSION COLUMNS: Identify categorical/text columns useful for grouping and segmentation (e.g., country, category, campaign, user_type, education, marital_status). These are typically text or low-cardinality values.

3. METRIC COLUMNS: Identify numeric columns that represent measurable values to aggregate (e.g., revenue, sales, count, amount, price, quantity). These should be numbers that make sense to sum or average.

IMPORTANT: 
- A column should NOT be both a dimension AND a metric
- ID columns are usually dimensions (for counting unique), not metrics
- Year columns might be dimensions, not dates
- Income, amount, count columns are typically metrics

Respond ONLY with this exact JSON format (no markdown, no explanation):
{{"date_column": "column_name", "dimensions": ["col1", "col2"], "metrics": ["col3", "col4"], "analysis_notes": "Brief explanation of your choices"}}
"""
        
        # Call Gemini
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Parse response
        response_text = response.text.strip()
        # Clean up markdown if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        # Calculate suggested date range (last 14 days split into two 7-day periods)
        from datetime import datetime, timedelta
        today = datetime.now()
        suggested_date_range = {
            "current_start": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
            "current_end": today.strftime("%Y-%m-%d"),
            "previous_start": (today - timedelta(days=14)).strftime("%Y-%m-%d"),
            "previous_end": (today - timedelta(days=8)).strftime("%Y-%m-%d")
        }
        
        return ColumnAnalysis(
            date_column=result.get("date_column", ""),
            dimensions=result.get("dimensions", []),
            metrics=result.get("metrics", []),
            suggested_date_range=suggested_date_range,
            analysis_notes=result.get("analysis_notes", "")
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed to return valid JSON: {str(e)}")
    except Exception as e:
        logger.error(f"CSV analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"CSV analysis failed: {str(e)}")


@app.post("/generate-report", response_model=ReportResponse, tags=["Reports"])
async def generate_report_endpoint(
    config_file: UploadFile = File(..., description="YAML configuration file"),
    csv_file: UploadFile = File(None, description="Optional CSV data file for direct upload")
) -> ReportResponse:
    """
    Generate an insight report from uploaded configuration.
    
    This endpoint:
    1. Reads the uploaded YAML config
    2. Loads and joins CSV data sources (or uses uploaded CSV)
    3. Computes derived metrics
    4. Splits data by time period
    5. Generates insights with deltas and impact scores
    6. Sends insights to LLM for narrative generation
    7. Creates a downloadable PPTX report
    
    Args:
        config_file: Uploaded YAML configuration file
        csv_file: Optional uploaded CSV data file
        
    Returns:
        ReportResponse with download URL
        
    Raises:
        HTTPException: On processing errors
    """
    logger.info(f"Received report generation request with config: {config_file.filename}")
    if csv_file:
        logger.info(f"CSV file uploaded: {csv_file.filename}")
    
    temp_config_path = None
    temp_csv_path = None
    
    try:
        # Read config content
        config_content = await config_file.read()
        config_str = config_content.decode("utf-8")
        
        # Parse and validate config
        try:
            config = load_config_from_string(config_str)
            logger.info("Configuration validated successfully")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid configuration: {str(e)}"
            )
        
        # Save config temporarily for reference
        temp_config_path = tmp_dir / config_file.filename
        temp_config_path.write_text(config_str)
        
        # Handle uploaded CSV file
        if csv_file:
            csv_content = await csv_file.read()
            temp_csv_path = tmp_dir / "uploaded.csv"
            temp_csv_path.write_bytes(csv_content)
            base_path = str(tmp_dir)
            logger.info(f"Saved uploaded CSV to: {temp_csv_path}")
        else:
            # Determine base path for data files
            base_path = get_base_path_from_config(config, str(tmp_dir))
        
        logger.info(f"Using base path for data: {base_path}")
        
        # Step 1: Ingest data
        try:
            logger.info("Step 1: Ingesting data sources")
            df = ingest_data(config, base_path)
        except FileNotFoundError as e:
            logger.error(f"Data file not found: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Data file not found: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Data ingestion failed: {str(e)}"
            )
        
        # Step 2: Process metrics
        try:
            logger.info("Step 2: Processing metrics and splitting periods")
            current_df, previous_df = process_metrics(df, config)
        except Exception as e:
            logger.error(f"Metrics processing failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Metrics processing failed: {str(e)}"
            )
        
        # Step 3: Generate insights
        try:
            logger.info("Step 3: Generating insights")
            insights_data = generate_insights(current_df, previous_df, config)
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Insight generation failed: {str(e)}"
            )
        
        # Step 4: Generate narrative
        try:
            logger.info("Step 4: Generating narrative from LLM")
            narrative = generate_narrative(
                insights_data,
                api_key=settings.gemini_api_key or settings.openai_api_key,
                model=settings.llm_model,
                provider=settings.llm_provider
            )
        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Narrative generation failed: {str(e)}"
            )
        
        # Step 5: Create Dashboard Session with QR code
        dashboard_url = None
        qr_path = None
        session = None
        voice_result = None
        try:
            logger.info("Step 5: Creating dashboard session")
            sessions_path = str(project_root / "tmp" / "sessions")
            logger.info(f"Sessions path: {sessions_path}")
            session_manager = get_session_manager(sessions_path)
            
            # Prepare narrative dict for session - map NarrativeSection fields correctly
            narrative_dict = {
                "title": narrative.title,
                "summary": narrative.headline,  # headline is the summary
                "highlights": narrative.bullets,  # bullets are the highlights
                "recommendation": narrative.recommendation
            }
            
            # Create session
            session = session_manager.create_session(
                title=config.title,
                insights=insights_data.get("insights", []),
                metrics_summary=insights_data.get("summary", {}),
                narrative=narrative_dict
            )
            logger.info(f"Session created: {session.session_id}")
            
            # Generate voice briefing
            audio_dir = project_root / "static" / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            voice_result = generate_voice_briefing(
                narrative=narrative_dict,
                insights=insights_data.get("insights", []),
                output_dir=str(audio_dir),
                session_id=session.session_id,
                murf_api_key=os.getenv("MURF_API_KEY")
            )
            logger.info(f"Voice result: {voice_result}")
            
            if voice_result.get("audio_url"):
                session.audio_url = voice_result["audio_url"]
                session_manager.update_session(session)
            
            # Generate QR code
            base_url = "http://localhost:8000"
            qr_bytes, dashboard_url = generate_qr_for_dashboard(
                base_url=base_url,
                session_id=session.session_id,
                token=session.token,
                output_path=str(project_root / "tmp" / f"qr_{session.session_id}.png")
            )
            qr_path = str(project_root / "tmp" / f"qr_{session.session_id}.png")
            
            logger.info(f"Dashboard URL created: {dashboard_url}")
            
        except Exception as e:
            logger.warning(f"Dashboard session creation failed (non-fatal): {e}")
            import traceback
            traceback.print_exc()
        
        # Step 6: Generate PPTX report with QR code
        try:
            logger.info("Step 6: Building PowerPoint report")
            report_path = generate_report(
                narrative,
                insights_data,
                output_dir=str(reports_dir),
                dashboard_url=dashboard_url,
                qr_code_path=qr_path
            )
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Report generation failed: {str(e)}"
            )
        
        # Build download URL
        report_filename = Path(report_path).name
        download_url = f"/static/reports/{report_filename}"
        
        logger.info(f"Report generated successfully: {download_url}")
        
        # Build response with all info
        response_data = {
            "download_url": download_url,
            "message": "Report generated successfully"
        }
        
        # Add dashboard info if session was created
        if dashboard_url:
            response_data["dashboard_url"] = dashboard_url
        if session:
            response_data["session_id"] = session.session_id
            if session.audio_url:
                response_data["audio_url"] = session.audio_url
        if voice_result:
            if voice_result.get("audio_url"):
                response_data["audio_url"] = voice_result["audio_url"]
            elif voice_result.get("tts_script"):
                response_data["voice_script"] = voice_result["tts_script"]
        
        logger.info(f"Response data: {response_data}")
        return ReportResponse(**response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during report generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        if temp_config_path and temp_config_path.exists():
            try:
                temp_config_path.unlink()
            except:
                pass
        if temp_csv_path and temp_csv_path.exists():
            try:
                temp_csv_path.unlink()
            except:
                pass


# ============================================
# Dashboard API Endpoints
# ============================================

class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    session_id: str
    title: str
    created_at: str
    expires_at: str
    insights: list
    metrics_summary: dict
    narrative: dict
    voice_briefing: dict


@app.post("/api/dashboard/create", tags=["Dashboard"])
async def create_dashboard_session(
    title: str,
    insights: list,
    metrics_summary: dict,
    narrative: dict
) -> Dict[str, Any]:
    """Create a new dashboard session programmatically."""
    sessions_path = str(project_root / "tmp" / "sessions")
    session_manager = get_session_manager(sessions_path)
    
    session = session_manager.create_session(
        title=title,
        insights=insights,
        metrics_summary=metrics_summary,
        narrative=narrative
    )
    
    # Generate voice briefing
    audio_dir = project_root / "static" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    voice_result = generate_voice_briefing(
        narrative=narrative,
        insights=insights,
        output_dir=str(audio_dir),
        session_id=session.session_id,
        murf_api_key=os.getenv("MURF_API_KEY")
    )
    
    # Generate QR code
    base_url = "http://localhost:8000"  # Could be configured
    qr_bytes, dashboard_url = generate_qr_for_dashboard(
        base_url=base_url,
        session_id=session.session_id,
        token=session.token,
        output_path=str(tmp_dir / f"qr_{session.session_id}.png")
    )
    
    # Update session with audio and QR info
    session.audio_url = voice_result.get("audio_url")
    session.qr_code_path = str(tmp_dir / f"qr_{session.session_id}.png")
    session_manager.update_session(session)
    
    return {
        "session_id": session.session_id,
        "token": session.token,
        "dashboard_url": dashboard_url,
        "qr_code_url": f"/tmp/qr_{session.session_id}.png",
        "expires_at": session.expires_at
    }


@app.get("/api/dashboard/{session_id}", response_model=DashboardResponse, tags=["Dashboard"])
async def get_dashboard_data(session_id: str, token: str = None) -> DashboardResponse:
    """
    Get dashboard data for a session.
    
    Args:
        session_id: The session identifier
        token: Access token for authentication
        
    Returns:
        Dashboard data including insights, metrics, and voice briefing
    """
    sessions_path = str(project_root / "tmp" / "sessions")
    session_manager = get_session_manager(sessions_path)
    session = session_manager.get_session(session_id, token)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )
    
    # Generate voice briefing on-demand if not available
    voice_briefing = {}
    audio_dir = project_root / "static" / "audio"
    
    if session.audio_url:
        voice_briefing = {
            "audio_type": "murf",
            "audio_url": session.audio_url
        }
    else:
        # Generate browser TTS script
        from engine.voice_briefing import generate_briefing_script
        voice_briefing = {
            "audio_type": "browser_tts",
            "tts_script": generate_briefing_script(session.narrative, session.insights)
        }
    
    return DashboardResponse(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        expires_at=session.expires_at,
        insights=session.insights,
        metrics_summary=session.metrics_summary,
        narrative=session.narrative,
        voice_briefing=voice_briefing
    )


@app.get("/dashboard/{session_id}", tags=["Dashboard"])
async def serve_dashboard(session_id: str):
    """Serve the dashboard HTML page."""
    from fastapi.responses import FileResponse
    dashboard_path = project_root / "frontend" / "dashboard.html"
    
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return FileResponse(str(dashboard_path), media_type="text/html")


@app.get("/api/session/{session_id}/qr", tags=["Dashboard"])
async def get_session_qr(session_id: str, token: str = None):
    """Get QR code for a session."""
    from fastapi.responses import Response
    
    sessions_path = str(project_root / "tmp" / "sessions")
    session_manager = get_session_manager(sessions_path)
    session = session_manager.get_session(session_id, token)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Generate fresh QR code
    base_url = "http://localhost:8000"
    qr_bytes, _ = generate_qr_for_dashboard(
        base_url=base_url,
        session_id=session_id,
        token=session.token
    )
    
    return Response(content=qr_bytes, media_type="image/png")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    
    Args:
        request: The request that caused the error
        exc: The exception
        
    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Development server entry point
if __name__ == "__main__":
    import uvicorn
    
    # Change to project root for correct static file serving
    os.chdir(Path(__file__).parent.parent.parent)
    
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
