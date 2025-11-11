"""
API routes for managing calls.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
from database.database import get_db_session
from database.models import CallLog, Invoice, Client, CallStatus
from services.call_orchestrator import call_orchestrator
from services.vapi_service import vapi_service
from utils.logger import logger


router = APIRouter()


class ManualCallRequest(BaseModel):
    """Request model for manual call trigger."""
    invoice_id: str


class CallResponse(BaseModel):
    """Response model for call information."""
    id: int
    vapi_call_id: Optional[str]
    invoice_id: str
    client_name: str
    call_made_on: datetime
    call_status: str
    call_duration: Optional[int]
    summary: Optional[str]
    call_outcome: Optional[str]
    
    class Config:
        from_attributes = True


@router.post("/trigger")
async def trigger_manual_call(
    request: ManualCallRequest,
    db: Session = Depends(get_db_session)
):
    """
    Manually trigger a call for a specific invoice.
    
    Args:
        request: Manual call request with invoice_id
        db: Database session
        
    Returns:
        Call status
    """
    try:
        # Find invoice
        invoice = db.query(Invoice).filter(
            Invoice.invoice_id == request.invoice_id
        ).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        client = invoice.client
        
        # Prepare payment data
        payment_data = {
            'client_name': client.client_name,
            'company_name': client.company_name,
            'contact_number': client.contact_number,
            'invoice_id': invoice.invoice_id,
            'amount_due': invoice.amount_due,
            'due_date': invoice.due_date,
            'db_invoice_id': invoice.id
        }
        
        # Make the call
        await call_orchestrator.make_single_call(payment_data)
        
        return {
            "status": "success",
            "message": f"Call initiated for invoice {request.invoice_id}",
            "invoice_id": request.invoice_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering manual call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-all")
async def process_all_pending():
    """
    Trigger calls for all pending payments.
    
    This endpoint starts the automated calling process.
    """
    try:
        await call_orchestrator.process_pending_payments()
        
        return {
            "status": "success",
            "message": "Payment follow-up process started"
        }
        
    except Exception as e:
        logger.error(f"Error processing pending payments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[CallResponse])
async def get_all_calls(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """
    Get all call logs.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of call logs
    """
    calls = db.query(CallLog).offset(skip).limit(limit).all()
    
    # Format response
    response = []
    for call in calls:
        invoice = call.invoice
        client = invoice.client
        
        response.append({
            "id": call.id,
            "vapi_call_id": call.vapi_call_id,
            "invoice_id": invoice.invoice_id,
            "client_name": client.client_name,
            "call_made_on": call.call_made_on,
            "call_status": call.call_status.value,
            "call_duration": call.call_duration,
            "summary": call.summary,
            "call_outcome": call.call_outcome
        })
    
    return response


@router.get("/{call_id}")
async def get_call_details(
    call_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Get detailed information about a specific call.
    
    Args:
        call_id: Call log ID
        db: Database session
        
    Returns:
        Detailed call information
    """
    call = db.query(CallLog).filter(CallLog.id == call_id).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    invoice = call.invoice
    client = invoice.client
    
    return {
        "id": call.id,
        "vapi_call_id": call.vapi_call_id,
        "invoice": {
            "invoice_id": invoice.invoice_id,
            "amount_due": invoice.amount_due,
            "due_date": invoice.due_date.isoformat(),
            "payment_status": invoice.payment_status.value
        },
        "client": {
            "name": client.client_name,
            "company": client.company_name,
            "contact": client.contact_number,
            "email": client.email
        },
        "call_details": {
            "made_on": call.call_made_on.isoformat(),
            "duration": call.call_duration,
            "status": call.call_status.value,
            "recording_url": call.recording_url,
            "cost": call.cost
        },
        "transcript": call.transcript,
        "summary": call.summary,
        "outcome": {
            "payment_promised": call.payment_promised,
            "payment_promise_date": call.payment_promise_date.isoformat() if call.payment_promise_date else None,
            "needs_invoice_resend": call.needs_invoice_resend,
            "customer_disputed": call.customer_disputed,
            "dispute_reason": call.dispute_reason,
            "next_follow_up_date": call.next_follow_up_date.isoformat() if call.next_follow_up_date else None,
            "language_detected": call.language_detected,
            "customer_sentiment": call.customer_sentiment,
            "call_outcome": call.call_outcome
        }
    }


@router.get("/status/{vapi_call_id}")
async def get_call_status(vapi_call_id: str):
    """
    Get call status from Vapi API.
    
    Args:
        vapi_call_id: Vapi call ID
        
    Returns:
        Current call status
    """
    try:
        status = await vapi_service.get_call_status(vapi_call_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting call status: {e}")
        raise HTTPException(status_code=500, detail=str(e))