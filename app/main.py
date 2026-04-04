from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from datetime import datetime
from loguru import logger
import time

from app.config import settings
from app.models.schemas import ProcessingResult, ProcessingStatus
from app.phases.phase1_ingestion import IngestionPhase
from app.phases.phase2_agent import AgenticCleansingPhase
from app.phases.phase3_structuring import StructuringPhase
from app.utils.logging_config import setup_logging
from app.utils.error_handling import handle_errors, ProcessingError

# Setup logging
setup_logging(settings.log_level)

# Initialize phases
ingestion_phase = IngestionPhase()
cleansing_phase = AgenticCleansingPhase()
structuring_phase = StructuringPhase()

# In-memory storage for processing results (can be replaced with Redis)
PROCESSING_RESULTS = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Invoice Processing System")
    yield
    logger.info("Shutting down Invoice Processing System")

# Create FastAPI app
app = FastAPI(
    title="Intelligent Document Processing Pipeline",
    description="Process invoices, PDFs, and scanned documents with AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "invoice-processor",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/process")
@handle_errors
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> ProcessingResult:
    """
    Main processing endpoint - runs full pipeline on uploaded document
    
    Args:
        file: Uploaded document (PDF, image, text, email)
    
    Returns:
        ProcessingResult with extracted, cleaned, and structured data
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"Processing request {request_id} - File: {file.filename}")
    
    # Validate file
    ext = f".{file.filename.split('.')[-1].lower()}"
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {settings.allowed_extensions}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size} bytes"
        )
    
    processing_stages = {}
    result = None
    
    try:
        # PHASE 1: Extraction
        logger.info(f"[{request_id}] Phase 1: Starting extraction")
        start_time = time.time()
        raw_extraction = await ingestion_phase.process(
            content, file.filename, file.content_type
        )
        processing_stages["extraction"] = (time.time() - start_time) * 1000
        
        # PHASE 2: Cleansing
        logger.info(f"[{request_id}] Phase 2: Starting agentic cleansing")
        start_time = time.time()
        cleaned_data = await cleansing_phase.process(raw_extraction)
        processing_stages["cleansing"] = (time.time() - start_time) * 1000
        
        # PHASE 3: Structuring
        logger.info(f"[{request_id}] Phase 3: Starting JSON structuring")
        start_time = time.time()
        final_invoice = await structuring_phase.process(cleaned_data)
        processing_stages["structuring"] = (time.time() - start_time) * 1000
        
        # Log successful processing
        logger.info(f"[{request_id}] Processing complete in {sum(processing_stages.values()):.2f}ms")
        
        result = ProcessingResult(
            request_id=request_id,
            status=ProcessingStatus.COMPLETED,
            raw_extraction=raw_extraction,
            cleaned_data=cleaned_data,
            final_invoice=final_invoice,
            processing_stages=processing_stages
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Processing failed: {str(e)}")
        result = ProcessingResult(
            request_id=request_id,
            status=ProcessingStatus.FAILED,
            error=str(e),
            processing_stages=processing_stages
        )
    
    # Store result in memory
    PROCESSING_RESULTS[request_id] = result.dict()
    
    # Optional: Add background task for analytics
    background_tasks.add_task(log_processing_metrics, request_id, processing_stages)
    
    return result

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "max_file_size": settings.max_file_size,
            "allowed_extensions": settings.allowed_extensions,
            "ocr_engine": settings.ocr_engine
        }
    }

@app.get("/process/{request_id}")
async def get_processing_result(request_id: str):
    """Retrieve processing result by request ID"""
    if request_id not in PROCESSING_RESULTS:
        raise HTTPException(
            status_code=404,
            detail=f"Request ID {request_id} not found"
        )
    return PROCESSING_RESULTS[request_id]

async def log_processing_metrics(request_id: str, stages: dict):
    """Background task for logging metrics"""
    logger.info(f"Metrics for {request_id}: {stages}")

# Optional: Add web interface endpoint
@app.get("/ui")
async def ui_info():
    """Information about available UI interfaces"""
    return {
        "message": "FastAPI endpoints available at /docs",
        "streamlit_ui": "Run 'streamlit run streamlit_app.py' for web interface",
        "endpoints": {
            "process": "POST /process - Upload and process document",
            "health": "GET /health - System health check"
        }
    }