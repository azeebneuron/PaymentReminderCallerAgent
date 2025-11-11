"""
Database models for the AI Payment Caller application.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, 
    Boolean, Text, ForeignKey, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum


Base = declarative_base()


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    WILL_PAY = "will_pay"


class CallStatus(str, enum.Enum):
    """Call status enumeration."""
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    VOICEMAIL = "voicemail"
    IN_PROGRESS = "in_progress"


class Client(Base):
    """Client information."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    contact_number = Column(String(20), unique=True, nullable=False)
    email = Column(String(255))
    google_sheet_id = Column(String(255))  # Google Sheet ID for this client
    preferred_language = Column(String(50), default="hindi")  # hindi/english/marathi
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")


class Invoice(Base):
    """Invoice information."""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invoice_id = Column(String(100), unique=True, nullable=False)
    amount_due = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    remarks = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="invoices")
    call_logs = relationship("CallLog", back_populates="invoice", cascade="all, delete-orphan")


class CallLog(Base):
    """Call log information."""
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # Vapi call details
    vapi_call_id = Column(String(255), unique=True)
    call_made_on = Column(DateTime, default=datetime.utcnow)
    call_duration = Column(Integer)  # in seconds
    call_status = Column(Enum(CallStatus), default=CallStatus.IN_PROGRESS)
    
    # Call content
    transcript = Column(Text)
    summary = Column(Text)
    recording_url = Column(String(500))
    
    # Parsed outcomes
    payment_promised = Column(Boolean, default=False)
    payment_promise_date = Column(Date)
    needs_invoice_resend = Column(Boolean, default=False)
    customer_disputed = Column(Boolean, default=False)
    dispute_reason = Column(Text)
    next_follow_up_date = Column(Date)
    
    # Metadata
    language_detected = Column(String(50))
    customer_sentiment = Column(String(50))  # positive/neutral/negative/angry
    call_outcome = Column(String(50))  # successful/unsuccessful/needs_escalation
    cost = Column(Float)  # Call cost from Vapi
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="call_logs")


class DailyReport(Base):
    """Daily aggregated report."""
    __tablename__ = "daily_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, unique=True, nullable=False)
    
    total_calls = Column(Integer, default=0)
    successful_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    no_answer_calls = Column(Integer, default=0)
    
    payments_promised = Column(Integer, default=0)
    invoices_resent = Column(Integer, default=0)
    disputes_raised = Column(Integer, default=0)
    
    total_cost = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemLog(Base):
    """System activity logs."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_level = Column(String(20))  # INFO, WARNING, ERROR, CRITICAL
    module = Column(String(100))
    message = Column(Text)
    details = Column(Text)  # JSON string for additional details
    created_at = Column(DateTime, default=datetime.utcnow)