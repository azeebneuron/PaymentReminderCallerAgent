import sys
from pathlib import Path

# --- Setup Project Path ---
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
# --- End Setup Project Path ---

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from database.database import get_db
from database.models import CallLog, Invoice, Client, CallStatus, PaymentStatus
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload
from services.call_orchestrator import call_orchestrator
import asyncio


# Page configuration
st.set_page_config(
    page_title="Contigo Payment Caller - Home",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Main styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }

    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #333;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }

    /* Alert boxes */
    .alert-box {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }

    .alert-error {
        background-color: #fee;
        border-color: #f44;
        color: #c00;
    }

    .alert-warning {
        background-color: #fff3cd;
        border-color: #ffc107;
        color: #856404;
    }

    .alert-success {
        background-color: #d4edda;
        border-color: #28a745;
        color: #155724;
    }

    .alert-info {
        background-color: #d1ecf1;
        border-color: #17a2b8;
        color: #0c5460;
    }

    /* Quick action buttons */
    .quick-action-btn {
        display: inline-block;
        padding: 1rem 2rem;
        background-color: #1f77b4;
        color: white;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s;
        text-align: center;
        margin: 0.5rem;
    }

    .quick-action-btn:hover {
        background-color: #145a8d;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Client card */
    .client-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid #dee2e6;
    }

    .client-name {
        font-weight: 600;
        color: #333;
        font-size: 1.1rem;
    }

    .client-detail {
        color: #666;
        font-size: 0.9rem;
    }

    /* Status badges */
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-block;
    }

    .status-success {
        background-color: #d4edda;
        color: #155724;
    }

    .status-warning {
        background-color: #fff3cd;
        color: #856404;
    }

    .status-danger {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)


def get_today_summary():
    """Get comprehensive summary for today."""
    today = date.today()

    with get_db() as db:
        # Today's calls
        today_calls = db.query(CallLog).filter(
            func.date(CallLog.call_made_on) == today
        ).all()

        # Pending invoices
        pending_invoices = db.query(Invoice).filter(
            Invoice.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
        ).all()

        # Promises due today
        promises_due = db.query(CallLog).filter(
            and_(
                CallLog.payment_promise_date == today,
                CallLog.payment_promised == True
            )
        ).all()

        # Recent calls needing follow-up
        follow_ups_needed = db.query(CallLog).filter(
            and_(
                CallLog.next_follow_up_date == today,
                CallLog.call_status == CallStatus.COMPLETED
            )
        ).all()

        # Active clients
        active_clients = db.query(Client).filter(
            Client.google_sheet_id != None
        ).all()

        # Extract data while in session
        client_data = []
        for client in active_clients:
            client_invoices = db.query(Invoice).filter(
                and_(
                    Invoice.client_id == client.id,
                    Invoice.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
                )
            ).count()

            client_data.append({
                'id': client.id,
                'name': client.client_name,
                'company': client.company_name,
                'contact': client.contact_number,
                'sheet_id': client.google_sheet_id,
                'pending_count': client_invoices
            })

        summary = {
            'calls_made': len(today_calls),
            'calls_successful': sum(1 for c in today_calls if c.call_status == CallStatus.COMPLETED),
            'promises_received': sum(1 for c in today_calls if c.payment_promised),
            'total_pending_invoices': len(pending_invoices),
            'total_pending_amount': sum(inv.amount_due for inv in pending_invoices),
            'promises_due_today': len(promises_due),
            'follow_ups_needed': len(follow_ups_needed),
            'active_clients': client_data,
            'promises_due_details': [
                {
                    'client_name': p.invoice.client.client_name,
                    'invoice_id': p.invoice.invoice_id,
                    'amount': p.invoice.amount_due,
                    'promise_date': p.payment_promise_date
                } for p in promises_due
            ]
        }

        return summary


def get_alerts():
    """Get important alerts for the dashboard."""
    alerts = []
    today = date.today()

    with get_db() as db:
        # Overdue promises
        overdue_promises = db.query(CallLog).filter(
            and_(
                CallLog.payment_promise_date < today,
                CallLog.payment_promised == True,
                CallLog.invoice.has(payment_status=PaymentStatus.PENDING)
            )
        ).all()

        if overdue_promises:
            alerts.append({
                'type': 'error',
                'title': 'Overdue Payment Promises',
                'message': f'{len(overdue_promises)} customers have missed their payment promise dates. Immediate follow-up needed.',
                'count': len(overdue_promises)
            })

        # Failed calls needing retry
        failed_calls = db.query(CallLog).filter(
            and_(
                func.date(CallLog.call_made_on) == today,
                CallLog.call_status == CallStatus.FAILED
            )
        ).all()

        if failed_calls:
            alerts.append({
                'type': 'warning',
                'title': 'Failed Calls Today',
                'message': f'{len(failed_calls)} calls failed today. Consider retrying these customers.',
                'count': len(failed_calls)
            })

        # High-value overdue invoices (>100k, overdue >30 days)
        high_value_overdue = db.query(Invoice).filter(
            and_(
                Invoice.amount_due > 100000,
                Invoice.due_date < today - timedelta(days=30),
                Invoice.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
            )
        ).all()

        if high_value_overdue:
            total_amount = sum(inv.amount_due for inv in high_value_overdue)
            alerts.append({
                'type': 'warning',
                'title': 'High-Value Overdue Invoices',
                'message': f'{len(high_value_overdue)} invoices worth ₹{total_amount:,.2f} are overdue by more than 30 days.',
                'count': len(high_value_overdue)
            })

        # Promises due today
        promises_due = db.query(CallLog).filter(
            and_(
                CallLog.payment_promise_date == today,
                CallLog.payment_promised == True
            )
        ).all()

        if promises_due:
            alerts.append({
                'type': 'info',
                'title': 'Payment Promises Due Today',
                'message': f'{len(promises_due)} customers promised to pay today. Monitor incoming payments.',
                'count': len(promises_due)
            })

        # Success message if all clear
        if not alerts:
            alerts.append({
                'type': 'success',
                'title': 'All Clear',
                'message': 'No urgent alerts. Everything is running smoothly!',
                'count': 0
            })

    return alerts


def main():
    """Main dashboard home page."""

    # Header
    st.markdown('<p class="main-header">Contigo Payment Caller Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f"**Welcome back!** Today is {date.today().strftime('%A, %B %d, %Y')}")

    # Get summary data
    summary = get_today_summary()

    # Quick Actions Section
    st.markdown('<p class="section-header">Quick Actions</p>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Make Calls", use_container_width=True, type="primary"):
            st.switch_page("pages/2_Make_Calls.py")

    with col2:
        if st.button("View Call Logs", use_container_width=True):
            st.switch_page("pages/3_Call_Logs.py")

    with col3:
        if st.button("Manage Sheets", use_container_width=True):
            st.switch_page("pages/1_Sheet_Management.py")

    with col4:
        if st.button("Pending Invoices", use_container_width=True):
            st.switch_page("pages/4_Pending_Invoices.py")

    st.markdown("---")

    # Today's Summary Section
    st.markdown('<p class="section-header">Today\'s Summary</p>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Calls Made",
            value=summary['calls_made'],
            delta=f"{summary['calls_successful']} successful"
        )

    with col2:
        st.metric(
            label="Promises Received",
            value=summary['promises_received'],
            delta=f"{summary['promises_due_today']} due today"
        )

    with col3:
        st.metric(
            label="Pending Invoices",
            value=summary['total_pending_invoices']
        )

    with col4:
        st.metric(
            label="Total Pending Amount",
            value=f"₹{summary['total_pending_amount']:,.0f}"
        )

    st.markdown("---")

    # Alerts Section
    st.markdown('<p class="section-header">Alerts & Notifications</p>', unsafe_allow_html=True)

    alerts = get_alerts()

    for alert in alerts:
        alert_class = f"alert-{alert['type']}"
        st.markdown(
            f"""
            <div class="alert-box {alert_class}">
                <strong>{alert['title']}</strong><br>
                {alert['message']}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Active Clients Section
    st.markdown('<p class="section-header">Active Clients</p>', unsafe_allow_html=True)

    if summary['active_clients']:
        for client in summary['active_clients']:
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(
                    f"""
                    <div class="client-card">
                        <div class="client-name">{client['name']}</div>
                        <div class="client-detail">
                            Contact: {client['contact']} | Company: {client['company'] or 'N/A'} |
                            Pending: {client['pending_count']} invoice(s)
                        </div>
                        <div class="client-detail" style="font-size: 0.8rem; color: #999;">
                            Sheet ID: {client['sheet_id'][:20]}...
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                if st.button(f"Call Now", key=f"call_{client['id']}", use_container_width=True):
                    st.session_state['selected_client_id'] = client['id']
                    st.switch_page("pages/2_Make_Calls.py")
    else:
        st.info("No active clients yet. Add clients in the Sheet Management page.")
        if st.button("Add First Client"):
            st.switch_page("pages/1_Sheet_Management.py")

    st.markdown("---")

    # Promises Due Today Section
    if summary['promises_due_today'] > 0:
        st.markdown('<p class="section-header">Payment Promises Due Today</p>', unsafe_allow_html=True)

        for promise in summary['promises_due_details']:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**{promise['client_name']}**")
                st.caption(f"Invoice: {promise['invoice_id']}")

            with col2:
                st.write(f"₹{promise['amount']:,.2f}")

            with col3:
                st.markdown('<span class="status-badge status-warning">Due Today</span>', unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.caption("Contigo Solutions PVT LTD - AI Payment Caller System")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
