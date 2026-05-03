from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from backend.services.aggregator import aggregator
import logging

router = APIRouter(prefix="/api/aggregate", tags=["aggregation"])
logger = logging.getLogger(__name__)

class AggregateRequest(BaseModel):
    keywords: List[str]
    days: int = 3

class AggregateResponse(BaseModel):
    status: str
    message: str
    # Since it's a background task, we might not return the count immediately 
    # unless we want to wait. The user said "The response should return how many NEW jobs were found and scored".
    # This implies a synchronous call or we wait for it.
    new_jobs_count: int = 0

@router.post("/start", response_model=AggregateResponse)
async def start_aggregation(request: AggregateRequest):
    """
    Triggers the multi-source crawl and analysis for a set of keywords.
    """
    try:
        logger.info(f"Starting manual aggregation for keywords: {request.keywords}")
        # Running synchronously for now to return the count as requested
        count = await aggregator.run_discovery(request.keywords, request.days)
        
        return AggregateResponse(
            status="success",
            message=f"Aggregation completed for {request.keywords}",
            new_jobs_count=count
        )
    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
