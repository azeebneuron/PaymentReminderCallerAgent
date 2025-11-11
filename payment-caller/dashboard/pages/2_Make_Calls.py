import sys
from pathlib import Path
# Setup project path
current_dir = Path(__file__).parent.parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database.database import get_db
from database.models import Client, Invoice, PaymentStatus
from services.call_orchestrator import call_orchestrator
from services.google_sheets import google_sheets_service
import asyncio
# Page configuration
st.set_page_config(
page_title="Make Calls",
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
.invoice-card {
background-color: #f8f9fa;
padding: 1rem;
border-radius: 8px;
margin-bottom: 0.5rem;
border-left: 4px solid #1f77b4;
}
.priority-high {
border-left-color: #dc3545 !important;
}
.priority-medium {
border-left-color: #ffc107 !important;
}
.priority-low {
border-left-color: #28a745 !important;
}
.call-progress {
background-color: #e3f2fd;
padding: 1rem;
border-radius: 8px;
margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)
def get_pending_invoices_for_client(client_id):
"""Get pending invoices for a specific client."""
with get_db() as db:
client = db.query(Client).filter(Client.id == client_id).first()
if not client:
return None, []
# Get pending payments from Google Sheet
try:
pending_payments = google_sheets_service.get_pending_payments(sheet_id=client.google_sheet_id)
# Filter invoices that should be called (not in future follow-up, etc.)
callable_invoices = []
for payment in pending_payments:
# Check if invoice exists in DB and get call history
invoice = db.query(Invoice).filter(
Invoice.invoice_id == payment['invoice_id']
).first()
# Determine if we should call
should_call = True
skip_reason = None
if invoice:
# Check last call log
from database.models import CallLog
last_call = db.query(CallLog).filter(
CallLog.invoice_id == invoice.id
).order_by(CallLog.call_made_on.desc()).first()
if last_call:
# Skip if next follow-up is in future
if last_call.next_follow_up_date and last_call.next_follow_up_date > date.today():
should_call = False
skip_reason = f"Next follow-up: {last_call.next_follow_up_date}"
# Skip if called today
if last_call.call_made_on.date() == date.today():
should_call = False
skip_reason = "Already called today"
# Calculate priority
days_overdue = (date.today() - payment['due_date']).days if payment['due_date'] else 0
amount = payment['amount_due']
if amount > 100000 or days_overdue > 90:
priority = "high"
elif amount > 50000 or days_overdue > 30:
priority = "medium"
else:
priority = "low"
payment_info = {
'invoice_id': payment['invoice_id'],
'amount_due': payment['amount_due'],
'due_date': payment['due_date'],
'days_overdue': days_overdue,
'priority': priority,
'should_call': should_call,
'skip_reason': skip_reason,
'client_name': payment['client_name'],
'company_name': payment['company_name'],
'contact_number': payment['contact_number'],
'row_number': payment.get('row_number', 0),
'db_invoice_id': invoice.id if invoice else None
}
callable_invoices.append(payment_info)
return client, callable_invoices
except Exception as e:
st.error(f"Error fetching invoices: {e}")
return client, []
def calculate_priority_stats(invoices):
"""Calculate statistics by priority."""
high = sum(1 for inv in invoices if inv['priority'] == 'high' and inv['should_call'])
medium = sum(1 for inv in invoices if inv['priority'] == 'medium' and inv['should_call'])
low = sum(1 for inv in invoices if inv['priority'] == 'low' and inv['should_call'])
return {'high': high, 'medium': medium, 'low': low}
async def make_call_async(payment_data):
"""Make a single call asynchronously."""
try:
await call_orchestrator.make_single_call(payment_data)
return True, None
except Exception as e:
return False, str(e)
def main():
"""Make Calls page."""
st.markdown('<p class="main-header"> Make Payment Calls</p>', unsafe_allow_html=True)
st.markdown("Select clients and invoices to call. Preview before confirming.")
# Initialize session state
if 'call_mode' not in st.session_state:
st.session_state['call_mode'] = 'call_all'
if 'selected_invoices' not in st.session_state:
st.session_state['selected_invoices'] = []
if 'call_in_progress' not in st.session_state:
st.session_state['call_in_progress'] = False
# Load all clients
with get_db() as db:
clients = db.query(Client).filter(Client.google_sheet_id != None).all()
client_data = [
{'id': c.id, 'name': c.client_name, 'contact': c.contact_number, 'sheet_id': c.google_sheet_id}
for c in clients
]
if not client_data:
st.warning(" No clients configured yet. Please add clients in the Sheet Management page first.")
if st.button(" Add Client"):
st.switch_page("pages/1__Sheet_Management.py")
return
# Client selection
st.markdown('<p class="section-header">1️⃣ Select Client</p>', unsafe_allow_html=True)
# Check if client was pre-selected from home page
pre_selected_client_id = st.session_state.get('selected_client_id')
client_options = [f"{c['name']} ({c['contact']})" for c in client_data]
default_index = 0
if pre_selected_client_id:
for idx, c in enumerate(client_data):
if c['id'] == pre_selected_client_id:
default_index = idx
break
# Clear the pre-selection
del st.session_state['selected_client_id']
selected_client_str = st.selectbox(
"Choose a client",
client_options,
index=default_index
)
selected_client_id = client_data[client_options.index(selected_client_str)]['id']
# Load invoices for selected client
with st.spinner("Loading pending invoices..."):
client, invoices = get_pending_invoices_for_client(selected_client_id)
if not client:
st.error(" Client not found")
return
if not invoices:
st.success(f"🎉 No pending invoices for {client.client_name}!")
return
# Show statistics
st.markdown('<p class="section-header">2️⃣ Invoices Overview</p>', unsafe_allow_html=True)
callable_count = sum(1 for inv in invoices if inv['should_call'])
skipped_count = len(invoices) - callable_count
total_amount = sum(inv['amount_due'] for inv in invoices if inv['should_call'])
col1, col2, col3, col4 = st.columns(4)
with col1:
st.metric("Total Pending", len(invoices))
with col2:
st.metric("Ready to Call", callable_count)
with col3:
st.metric("Skipped", skipped_count)
with col4:
st.metric("Total Amount", f"₹{total_amount:,.0f}")
# Priority breakdown
priority_stats = calculate_priority_stats(invoices)
if priority_stats['high'] > 0 or priority_stats['medium'] > 0 or priority_stats['low'] > 0:
st.markdown("**Priority Breakdown:**")
col1, col2, col3 = st.columns(3)
with col1:
st.metric("🔴 High Priority", priority_stats['high'])
with col2:
st.metric("🟡 Medium Priority", priority_stats['medium'])
with col3:
st.metric("🟢 Low Priority", priority_stats['low'])
# Call mode selection
st.markdown('<p class="section-header">3️⃣ Select Calling Mode</p>', unsafe_allow_html=True)
call_mode = st.radio(
"Choose how to make calls",
[" Call All Pending", " Select Specific Invoices", " Schedule for Later"],
horizontal=True,
key="call_mode_radio"
)
st.session_state['call_mode'] = call_mode
# CALL ALL MODE
if call_mode == " Call All Pending":
st.markdown('<p class="section-header">4️⃣ Preview & Confirm</p>', unsafe_allow_html=True)
callable_invoices = [inv for inv in invoices if inv['should_call']]
if not callable_invoices:
st.info("No invoices ready to call at this time.")
st.markdown("**Reasons:**")
for inv in invoices:
if not inv['should_call']:
st.write(f"- {inv['invoice_id']}: {inv['skip_reason']}")
return
st.write(f"**Will call {len(callable_invoices)} customer(s):**")
# Show invoice list
for inv in callable_invoices:
priority_class = f"priority-{inv['priority']}"
st.markdown(
f"""
<div class="invoice-card {priority_class}">
<strong>{inv['invoice_id']}</strong> - ₹{inv['amount_due']:,.2f}<br>
Due: {inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A'} | {inv['days_overdue']} days overdue | Priority: {inv['priority'].upper()}
</div>
""",
unsafe_allow_html=True
)
st.warning(f" This will initiate {len(callable_invoices)} call(s). Calls will be rate-limited to avoid overwhelming the system.")
if st.button(" Confirm & Start Calling", type="primary", use_container_width=True, disabled=st.session_state.get('call_in_progress', False)):
st.session_state['call_in_progress'] = True
progress_bar = st.progress(0)
status_text = st.empty()
success_count = 0
failed_count = 0
for idx, inv in enumerate(callable_invoices):
status_text.write(f" Calling {inv['invoice_id']}... ({idx + 1}/{len(callable_invoices)})")
# Prepare payment data
payment_data = {
'client_name': inv['client_name'],
'company_name': inv['company_name'],
'contact_number': inv['contact_number'],
'invoice_id': inv['invoice_id'],
'amount_due': inv['amount_due'],
'due_date': inv['due_date'],
'db_invoice_id': inv['db_invoice_id'],
'row_number': inv['row_number']
}
# Make call
success, error = asyncio.run(make_call_async(payment_data))
if success:
success_count += 1
status_text.success(f" Call initiated for {inv['invoice_id']}")
else:
failed_count += 1
status_text.error(f" Failed to call {inv['invoice_id']}: {error}")
# Update progress
progress_bar.progress((idx + 1) / len(callable_invoices))
# Rate limiting delay
if idx < len(callable_invoices) - 1:
import time
time.sleep(2) # 2 second delay between calls
st.session_state['call_in_progress'] = False
# Final summary
st.markdown("---")
st.markdown("### Call Summary")
col1, col2 = st.columns(2)
with col1:
st.metric(" Successful", success_count)
with col2:
st.metric(" Failed", failed_count)
if success_count > 0:
st.success(f"🎉 Successfully initiated {success_count} call(s)! Check the Call Logs page for updates.")
if failed_count > 0:
st.warning(f" {failed_count} call(s) failed. Please check the logs.")
# SELECT SPECIFIC MODE
elif call_mode == " Select Specific Invoices":
st.markdown('<p class="section-header">4️⃣ Select Invoices to Call</p>', unsafe_allow_html=True)
callable_invoices = [inv for inv in invoices if inv['should_call']]
if not callable_invoices:
st.info("No invoices ready to call at this time.")
return
st.write("**Select invoices to call:**")
selected = []
for inv in callable_invoices:
priority_class = f"priority-{inv['priority']}"
col1, col2 = st.columns([1, 10])
with col1:
is_selected = st.checkbox("", key=f"select_{inv['invoice_id']}")
if is_selected:
selected.append(inv)
with col2:
st.markdown(
f"""
<div class="invoice-card {priority_class}">
<strong>{inv['invoice_id']}</strong> - ₹{inv['amount_due']:,.2f}<br>
Due: {inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A'} | {inv['days_overdue']} days overdue | Priority: {inv['priority'].upper()}
</div>
""",
unsafe_allow_html=True
)
if selected:
st.markdown('<p class="section-header">5️⃣ Preview & Confirm</p>', unsafe_allow_html=True)
st.write(f"**Selected {len(selected)} invoice(s) to call:**")
for inv in selected:
st.write(f"- {inv['invoice_id']} (₹{inv['amount_due']:,.2f})")
if st.button(" Call Selected Invoices", type="primary", use_container_width=True, disabled=st.session_state.get('call_in_progress', False)):
st.session_state['call_in_progress'] = True
progress_bar = st.progress(0)
status_text = st.empty()
success_count = 0
failed_count = 0
for idx, inv in enumerate(selected):
status_text.write(f" Calling {inv['invoice_id']}... ({idx + 1}/{len(selected)})")
# Prepare payment data
payment_data = {
'client_name': inv['client_name'],
'company_name': inv['company_name'],
'contact_number': inv['contact_number'],
'invoice_id': inv['invoice_id'],
'amount_due': inv['amount_due'],
'due_date': inv['due_date'],
'db_invoice_id': inv['db_invoice_id'],
'row_number': inv['row_number']
}
# Make call
success, error = asyncio.run(make_call_async(payment_data))
if success:
success_count += 1
status_text.success(f" Call initiated for {inv['invoice_id']}")
else:
failed_count += 1
status_text.error(f" Failed to call {inv['invoice_id']}: {error}")
# Update progress
progress_bar.progress((idx + 1) / len(selected))
# Rate limiting delay
if idx < len(selected) - 1:
import time
time.sleep(2)
st.session_state['call_in_progress'] = False
# Final summary
st.markdown("---")
st.markdown("### Call Summary")
col1, col2 = st.columns(2)
with col1:
st.metric(" Successful", success_count)
with col2:
st.metric(" Failed", failed_count)
if success_count > 0:
st.success(f"🎉 Successfully initiated {success_count} call(s)!")
else:
st.info("👆 Select at least one invoice to proceed")
# SCHEDULE MODE
elif call_mode == " Schedule for Later":
st.markdown('<p class="section-header">4️⃣ Schedule Calls</p>', unsafe_allow_html=True)
callable_invoices = [inv for inv in invoices if inv['should_call']]
if not callable_invoices:
st.info("No invoices ready to call at this time.")
return
col1, col2 = st.columns(2)
with col1:
schedule_date = st.date_input(
"Select Date",
min_value=date.today(),
value=date.today()
)
with col2:
schedule_time = st.time_input(
"Select Time",
value=datetime.now().time()
)
st.write(f"**Will schedule {len(callable_invoices)} call(s) for {schedule_date} at {schedule_time}**")
# Show invoice list
for inv in callable_invoices:
priority_class = f"priority-{inv['priority']}"
st.markdown(
f"""
<div class="invoice-card {priority_class}">
<strong>{inv['invoice_id']}</strong> - ₹{inv['amount_due']:,.2f}<br>
Due: {inv['due_date'].strftime('%Y-%m-%d') if inv['due_date'] else 'N/A'} | Priority: {inv['priority'].upper()}
</div>
""",
unsafe_allow_html=True
)
st.info("🚧 **Scheduling feature coming soon!** For now, use 'Call All Pending' or 'Select Specific' to make immediate calls.")
# TODO: Implement actual scheduling with a task queue (Celery, APScheduler, etc.)
# if st.button(" Schedule Calls", type="primary", use_container_width=True):
# st.success(f" Scheduled {len(callable_invoices)} call(s) for {schedule_date} at {schedule_time}")
# Footer
st.markdown("---")
st.caption(" **Tip**: Calls are rate-limited to prevent overwhelming customers. High-priority invoices (high amount or long overdue) are marked in red.")
if __name__ == "__main__":
main()
