import sys
from pathlib import Path
# Setup project path
current_dir = Path(__file__).parent.parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
import streamlit as st
import pandas as pd
from datetime import date
from database.database import get_db
from database.models import Invoice, Client, PaymentStatus
from sqlalchemy.orm import joinedload
# Page configuration
st.set_page_config(
page_title="Pending Invoices",
page_icon="",
layout="wide"
)
# Shared CSS
st.markdown("""
<style>
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
.priority-badge {
padding: 0.25rem 0.75rem;
border-radius: 12px;
font-size: 0.85rem;
font-weight: 600;
display: inline-block;
}
.badge-high {
background-color: #dc3545;
color: white;
}
.badge-medium {
background-color: #ffc107;
color: #333;
}
.badge-low {
background-color: #28a745;
color: white;
}
</style>
""", unsafe_allow_html=True)
def calculate_priority(amount, days_overdue):
"""Calculate invoice priority based on amount and days overdue."""
if amount > 100000 or days_overdue > 90:
return "high", "🔴 High"
elif amount > 50000 or days_overdue > 30:
return "medium", "🟡 Medium"
else:
return "low", "🟢 Low"
def main():
"""Pending Invoices page."""
st.markdown('<p class="main-header"> Pending Invoices</p>', unsafe_allow_html=True)
st.markdown("View and manage all pending payment invoices, categorized by priority.")
# Load data
invoices_data = []
today = date.today()
with get_db() as db:
invoices = db.query(Invoice).options(
joinedload(Invoice.client)
).filter(
Invoice.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
).all()
if not invoices:
st.success("🎉 No pending invoices! All payments are up to date.")
return
# Extract data
for inv in invoices:
days_overdue = (today - inv.due_date).days if inv.due_date else 0
priority, priority_label = calculate_priority(inv.amount_due, days_overdue)
invoices_data.append({
'client_name': inv.client.client_name,
'company_name': inv.client.company_name or 'N/A',
'contact': inv.client.contact_number,
'invoice_id': inv.invoice_id,
'amount_due': inv.amount_due,
'due_date': inv.due_date,
'days_overdue': days_overdue,
'payment_status': inv.payment_status.value,
'priority': priority,
'priority_label': priority_label
})
# Overall Statistics
st.markdown('<p class="section-header"> Overview</p>', unsafe_allow_html=True)
total_pending = len(invoices_data)
total_amount = sum(inv['amount_due'] for inv in invoices_data)
avg_amount = total_amount / total_pending if total_pending > 0 else 0
avg_overdue_days = sum(inv['days_overdue'] for inv in invoices_data) / total_pending if total_pending > 0 else 0
col1, col2, col3, col4 = st.columns(4)
with col1:
st.metric("Pending Invoices", total_pending)
with col2:
st.metric("Total Amount", f"₹{total_amount:,.0f}")
with col3:
st.metric("Average Amount", f"₹{avg_amount:,.0f}")
with col4:
st.metric("Avg Days Overdue", f"{avg_overdue_days:.0f}")
# Priority Breakdown
st.markdown('<p class="section-header"> Priority Breakdown</p>', unsafe_allow_html=True)
high_priority = [inv for inv in invoices_data if inv['priority'] == 'high']
medium_priority = [inv for inv in invoices_data if inv['priority'] == 'medium']
low_priority = [inv for inv in invoices_data if inv['priority'] == 'low']
col1, col2, col3 = st.columns(3)
with col1:
high_amount = sum(inv['amount_due'] for inv in high_priority)
st.metric(
"🔴 High Priority",
len(high_priority),
delta=f"₹{high_amount:,.0f}"
)
with col2:
medium_amount = sum(inv['amount_due'] for inv in medium_priority)
st.metric(
"🟡 Medium Priority",
len(medium_priority),
delta=f"₹{medium_amount:,.0f}"
)
with col3:
low_amount = sum(inv['amount_due'] for inv in low_priority)
st.metric(
"🟢 Low Priority",
len(low_priority),
delta=f"₹{low_amount:,.0f}"
)
# Categorized Invoices
st.markdown('<p class="section-header"> Invoices by Priority</p>', unsafe_allow_html=True)
# High Priority
if high_priority:
with st.expander(f"🔴 High Priority ({len(high_priority)} invoices) - ₹{high_amount:,.0f}", expanded=True):
high_df = pd.DataFrame([
{
'Client': inv['client_name'],
'Company': inv['company_name'],
'Contact': inv['contact'],
'Invoice ID': inv['invoice_id'],
'Amount': f"₹{inv['amount_due']:,.2f}",
'Due Date': inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A',
'Days Overdue': inv['days_overdue'],
'Status': inv['payment_status']
}
for inv in high_priority
])
st.dataframe(high_df, use_container_width=True, height=300)
# Medium Priority
if medium_priority:
with st.expander(f"🟡 Medium Priority ({len(medium_priority)} invoices) - ₹{medium_amount:,.0f}"):
medium_df = pd.DataFrame([
{
'Client': inv['client_name'],
'Company': inv['company_name'],
'Contact': inv['contact'],
'Invoice ID': inv['invoice_id'],
'Amount': f"₹{inv['amount_due']:,.2f}",
'Due Date': inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A',
'Days Overdue': inv['days_overdue'],
'Status': inv['payment_status']
}
for inv in medium_priority
])
st.dataframe(medium_df, use_container_width=True, height=300)
# Low Priority
if low_priority:
with st.expander(f"🟢 Low Priority ({len(low_priority)} invoices) - ₹{low_amount:,.0f}"):
low_df = pd.DataFrame([
{
'Client': inv['client_name'],
'Company': inv['company_name'],
'Contact': inv['contact'],
'Invoice ID': inv['invoice_id'],
'Amount': f"₹{inv['amount_due']:,.2f}",
'Due Date': inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A',
'Days Overdue': inv['days_overdue'],
'Status': inv['payment_status']
}
for inv in low_priority
])
st.dataframe(low_df, use_container_width=True, height=300)
# Download All
st.markdown("---")
all_invoices_df = pd.DataFrame([
{
'Priority': inv['priority_label'],
'Client': inv['client_name'],
'Company': inv['company_name'],
'Contact': inv['contact'],
'Invoice ID': inv['invoice_id'],
'Amount': inv['amount_due'],
'Due Date': inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A',
'Days Overdue': inv['days_overdue'],
'Status': inv['payment_status']
}
for inv in invoices_data
])
csv = all_invoices_df.to_csv(index=False)
st.download_button(
label=" Download All Pending Invoices (CSV)",
data=csv,
file_name=f"pending_invoices_{date.today()}.csv",
mime="text/csv",
use_container_width=False
)
# Footer
st.markdown("---")
st.caption(" **Priority Calculation**: High (>₹100k or >90 days overdue), Medium (>₹50k or >30 days), Low (others)")
if __name__ == "__main__":
main()
