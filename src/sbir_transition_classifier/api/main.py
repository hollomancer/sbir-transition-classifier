from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from ..detection.main import run_full_detection
from ..data.schemas import DetectRequest
from ..db.database import SessionLocal
import uuid

app = FastAPI(
    title="SBIR Transition Detection API",
    description="API for detecting and retrieving evidence of untagged SBIR Phase III transitions.",
    version="1.0.0"
)

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning(f"Validation error for request {request.url}: {exc}")
    return JSONResponse(
        status_code=422,
        content={"message": "Validation error", "details": exc.errors()},
    )

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error for request {request.url}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"message": "Database service temporarily unavailable"},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception for request {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred."},
    )

@app.post("/detect", status_code=202)
def trigger_detection(request: DetectRequest, background_tasks: BackgroundTasks):
    """
    Triggers a full, asynchronous detection process.
    """
    try:
        # Validate identifier format if provided
        vendor_id_valid = request.vendor_identifier and len(request.vendor_identifier.strip()) > 0
        sbir_id_valid = request.sbir_award_piid and len(request.sbir_award_piid.strip()) > 0
        
        if not vendor_id_valid and not sbir_id_valid:
            raise HTTPException(status_code=400, detail="Either vendor_identifier or sbir_award_piid must be provided.")

        if request.vendor_identifier and not vendor_id_valid:
            raise HTTPException(status_code=400, detail="vendor_identifier cannot be empty")
        
        if request.sbir_award_piid and not sbir_id_valid:
            raise HTTPException(status_code=400, detail="sbir_award_piid cannot be empty")

        task_id = uuid.uuid4()
        # In a real application, you would use a proper task queue like Celery
        # and store the task status.
        # Also, you would pass the request parameters to the background task.
        background_tasks.add_task(run_full_detection)
        logger.info(f"Triggered background task {task_id} for full detection run.")
        return {"task_id": str(task_id), "status": "Analysis has been accepted and is in progress."}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in trigger_detection: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate detection process")

@app.get("/evidence/{detection_id}")
def get_evidence(detection_id: uuid.UUID):
    """
    Fetches the detailed evidence bundle for a specific detection ID.
    """
    logger.info(f"Fetching evidence for detection_id: {detection_id}")
    db = SessionLocal()
    try:
        # Import models properly
        from ..core.models import Detection
        detection_record = db.query(Detection).filter(Detection.id == detection_id).first()
        if not detection_record:
            raise HTTPException(status_code=404, detail="Detection not found")
        return detection_record.evidence_bundle
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching detection {detection_id}: {e}")
        raise HTTPException(status_code=503, detail="Database service temporarily unavailable")
    except Exception as e:
        logger.error(f"Error fetching evidence for detection {detection_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evidence")
    finally:
        db.close()
