"""
Vapi webhook handler for receiving call updates.
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
from services.call_orchestrator import call_orchestrator
from utils.logger import logger


router = APIRouter()


@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Webhook endpoint to receive updates from Vapi.
    
    This endpoint receives various call events from Vapi:
    - status-update: Call status changes
    - transcript: Real-time transcript updates
    - end-of-call-report: Final call summary and transcript
    """
    try:
        # Get webhook payload
        payload = await request.json()
        
        logger.info(f"Received webhook: {payload.get('message', {}).get('type', 'unknown')}")
        
        # Process the webhook
        call_orchestrator.process_call_webhook(payload)
        
        return {"status": "received", "message": "Webhook processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible."""
    return {
        "status": "ok",
        "message": "Webhook endpoint is accessible",
        "url": "/vapi/webhook"
    }