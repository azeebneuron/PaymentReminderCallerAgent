"""
API routes for reports and analytics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import Optional
from database.database import get_db_session
from database.models import CallLog, Invoice, Client, CallStatus, PaymentStatus
from utils.logger import logger


router = APIRouter()


@router.get("/daily")
async def get_daily_report(
    report_date: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    Get daily report for a specific date.
    
    Args:
        report_date: Date in YYYY-MM-DD format (defaults to today)
        db: Database session
        
    Returns:
        Daily report statistics
    """
    if report_date:
        target_date = datetime.strptime(report_date, "%Y-%m-%d").date()
    else:
        target_date = date.today()
    
    # Get calls for the date
    calls = db.query(CallLog).filter(
        func.date(CallLog.call_made_on) == target_date
    ).all()
    
    # Calculate statistics
    total_calls = len(calls)
    successful_calls = sum(1 for c in calls if c.call_status == CallStatus.COMPLETED)
    failed_calls = sum(1 for c in calls if c.call_status == CallStatus.FAILED)
    no_answer_calls = sum(1 for c in calls if c.call_status == CallStatus.NO_ANSWER)
    
    payments_promised = sum(1 for c in calls if c.payment_promised)
    invoices_resent = sum(1 for c in calls if c.needs_invoice_resend)
    disputes_raised = sum(1 for c in calls if c.customer_disputed)
    
    total_cost = sum(c.cost for c in calls if c.cost)
    total_duration = sum(c.call_duration for c in calls if c.call_duration)
    
    # Language breakdown
    languages = {}
    for call in calls:
        lang = call.language_detected or "unknown"
        languages[lang] = languages.get(lang, 0) + 1
    
    # Sentiment breakdown
    sentiments = {}
    for call in calls:
        sentiment = call.customer_sentiment or "neutral"
        sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
    
    return {
        "date": target_date.isoformat(),
        "summary": {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "no_answer_calls": no_answer_calls,
            "success_rate": f"{(successful_calls/total_calls*100):.1f}%" if total_calls > 0 else "0%"
        },
        "outcomes": {
            "payments_promised": payments_promised,
            "invoices_resent": invoices_resent,
            "disputes_raised": disputes_raised
        },
        "costs": {
            "total_cost": round(total_cost, 2),
            "average_cost_per_call": round(total_cost / total_calls, 2) if total_calls > 0 else 0
        },
        "duration": {
            "total_minutes": round(total_duration / 60, 1) if total_duration else 0,
            "average_duration_seconds": round(total_duration / total_calls, 1) if total_calls > 0 else 0
        },
        "languages": languages,
        "sentiment": sentiments
    }


@router.get("/weekly")
async def get_weekly_report(db: Session = Depends(get_db_session)):
    """
    Get weekly report for the last 7 days.
    
    Args:
        db: Database session
        
    Returns:
        Weekly report statistics
    """
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # Get calls for the week
    calls = db.query(CallLog).filter(
        func.date(CallLog.call_made_on) >= week_ago,
        func.date(CallLog.call_made_on) <= today
    ).all()
    
    # Daily breakdown
    daily_stats = {}
    for i in range(7):
        day = week_ago + timedelta(days=i)
        day_calls = [c for c in calls if c.call_made_on.date() == day]
        
        daily_stats[day.isoformat()] = {
            "total_calls": len(day_calls),
            "successful": sum(1 for c in day_calls if c.call_status == CallStatus.COMPLETED),
            "payments_promised": sum(1 for c in day_calls if c.payment_promised)
        }
    
    return {
        "period": f"{week_ago.isoformat()} to {today.isoformat()}",
        "total_calls": len(calls),
        "daily_breakdown": daily_stats
    }


@router.get("/pending-invoices")
async def get_pending_invoices(db: Session = Depends(get_db_session)):
    """
    Get all pending invoices summary.
    
    Args:
        db: Database session
        
    Returns:
        Pending invoices statistics
    """
    pending_invoices = db.query(Invoice).filter(
        Invoice.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
    ).all()
    
    total_pending = len(pending_invoices)
    total_amount = sum(inv.amount_due for inv in pending_invoices)
    
    # Categorize by days overdue
    today = date.today()
    overdue_categories = {
        "0-7_days": [],
        "8-15_days": [],
        "16-30_days": [],
        "30+_days": []
    }
    
    for invoice in pending_invoices:
        days_overdue = (today - invoice.due_date).days
        
        if days_overdue <= 7:
            overdue_categories["0-7_days"].append(invoice)
        elif days_overdue <= 15:
            overdue_categories["8-15_days"].append(invoice)
        elif days_overdue <= 30:
            overdue_categories["16-30_days"].append(invoice)
        else:
            overdue_categories["30+_days"].append(invoice)
    
    return {
        "total_pending_invoices": total_pending,
        "total_amount_pending": round(total_amount, 2),
        "categories": {
            category: {
                "count": len(invoices),
                "amount": round(sum(inv.amount_due for inv in invoices), 2)
            }
            for category, invoices in overdue_categories.items()
        }
    }


@router.get("/client-history/{client_id}")
async def get_client_call_history(
    client_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Get call history for a specific client.
    
    Args:
        client_id: Client ID
        db: Database session
        
    Returns:
        Client call history
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        return {"error": "Client not found"}
    
    invoices = client.invoices
    
    call_history = []
    for invoice in invoices:
        for call in invoice.call_logs:
            call_history.append({
                "call_date": call.call_made_on.isoformat(),
                "invoice_id": invoice.invoice_id,
                "amount_due": invoice.amount_due,
                "call_outcome": call.call_outcome,
                "payment_promised": call.payment_promised,
                "summary": call.summary
            })
    
    return {
        "client": {
            "name": client.client_name,
            "company": client.company_name,
            "contact": client.contact_number
        },
        "total_calls": len(call_history),
        "call_history": sorted(call_history, key=lambda x: x["call_date"], reverse=True)
    }