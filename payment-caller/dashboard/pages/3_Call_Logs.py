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
from database.models import CallLog, Invoice, Client, CallStatus
from sqlalchemy import func
from sqlalchemy.orm import joinedload
# Page configuration
st.set_page_config(
page_title="Call Logs",
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
</style>
""", unsafe_allow_html=True)
def main():
"""Call Logs page."""
st.markdown('<p class="main-header"> Call Logs</p>', unsafe_allow_html=True)
st.markdown("View detailed logs of all payment reminder calls.")
# Filters Section
st.markdown('<p class="section-header"> Filters</p>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
status_filter = st.selectbox(
"Status",
["All", "completed", "failed", "no_answer", "in_progress"]
)
with col2:
language_filter = st.selectbox(
"Language",
["All", "hindi", "english", "marathi", "mixed"]
)
with col3:
sentiment_filter = st.selectbox(
"Sentiment",
["All", "positive", "neutral", "negative", "angry"]
)
with col4:
date_range = st.selectbox(
"Date Range",
["Today", "Last 7 Days", "Last 30 Days", "All Time"]
)
# Load and filter data
call_data = []
detailed_calls = []
with get_db() as db:
# Base query with eager loading
calls_query = db.query(CallLog).options(
joinedload(CallLog.invoice).joinedload(Invoice.client)
).order_by(CallLog.call_made_on.desc())
# Apply filters
if status_filter != "All":
calls_query = calls_query.filter(CallLog.call_status == status_filter)
if language_filter != "All":
calls_query = calls_query.filter(CallLog.language_detected == language_filter)
if sentiment_filter != "All":
calls_query = calls_query.filter(CallLog.customer_sentiment == sentiment_filter)
# Date range filter
if date_range == "Today":
calls_query = calls_query.filter(func.date(CallLog.call_made_on) == date.today())
elif date_range == "Last 7 Days":
calls_query = calls_query.filter(CallLog.call_made_on >= datetime.now() - timedelta(days=7))
elif date_range == "Last 30 Days":
calls_query = calls_query.filter(CallLog.call_made_on >= datetime.now() - timedelta(days=30))
calls = calls_query.limit(200).all()
if not calls:
st.info("No call logs match the selected filters.")
return
# Extract data while in session
for call in calls:
invoice = call.invoice
client = invoice.client
call_data.append({
'Date': call.call_made_on.strftime('%Y-%m-%d %H:%M'),
'Client': client.client_name,
'Company': client.company_name or 'N/A',
'Invoice': invoice.invoice_id,
'Amount': f"₹{invoice.amount_due:,.2f}",
'Status': call.call_status.value,
'Duration (s)': call.call_duration or 0,
'Language': call.language_detected or 'N/A',
'Sentiment': call.customer_sentiment or 'N/A',
'Payment Promised': '' if call.payment_promised else '',
'Outcome': call.call_outcome or 'N/A',
'Cost': f"₹{call.cost:.4f}" if call.cost else 'N/A'
})
# Store full objects for detailed view
detailed_calls = calls
# Statistics
st.markdown('<p class="section-header"> Statistics</p>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
st.metric("Total Calls", len(call_data))
with col2:
successful = sum(1 for c in detailed_calls if c.call_status == CallStatus.COMPLETED)
st.metric("Successful", successful)
with col3:
promises = sum(1 for c in detailed_calls if c.payment_promised)
st.metric("Promises Received", promises)
with col4:
total_cost = sum(c.cost for c in detailed_calls if c.cost)
st.metric("Total Cost", f"₹{total_cost:.2f}")
# Call Logs Table
st.markdown('<p class="section-header"> Call History</p>', unsafe_allow_html=True)
if call_data:
df = pd.DataFrame(call_data)
st.dataframe(df, use_container_width=True, height=400)
# Download button
csv = df.to_csv(index=False)
st.download_button(
label=" Download CSV",
data=csv,
file_name=f"call_logs_{date.today()}.csv",
mime="text/csv",
use_container_width=False
)
# Detailed View
st.markdown('<p class="section-header"> Call Details</p>', unsafe_allow_html=True)
if detailed_calls:
call_ids = [
f"{c.invoice.client.client_name} - {c.invoice.invoice_id} - {c.call_made_on.strftime('%Y-%m-%d %H:%M')} (ID: {c.id})"
for c in detailed_calls
]
selected_call_str = st.selectbox("Select a call to view details", call_ids)
if selected_call_str:
selected_index = call_ids.index(selected_call_str)
call = detailed_calls[selected_index]
# Call Information Cards
col1, col2 = st.columns(2)
with col1:
st.markdown("#### Call Information")
st.write(f"**Call ID:** {call.vapi_call_id}")
st.write(f"**Date:** {call.call_made_on.strftime('%Y-%m-%d %H:%M:%S')}")
st.write(f"**Duration:** {call.call_duration}s" if call.call_duration else "**Duration:** N/A")
st.write(f"**Status:** {call.call_status.value}")
st.write(f"**Cost:** ₹{call.cost:.4f}" if call.cost else "**Cost:** N/A")
if call.recording_url:
st.markdown(f"[🎧 **Listen to Recording**]({call.recording_url})")
with col2:
st.markdown("#### Outcome")
st.write(f"**Language:** {call.language_detected or 'N/A'}")
st.write(f"**Sentiment:** {call.customer_sentiment or 'N/A'}")
st.write(f"**Call Outcome:** {call.call_outcome or 'N/A'}")
st.write(f"**Payment Promised:** {' Yes' if call.payment_promised else ' No'}")
if call.payment_promise_date:
st.write(f"**Promise Date:** {call.payment_promise_date.strftime('%Y-%m-%d')}")
if call.next_follow_up_date:
st.write(f"**Next Follow-up:** {call.next_follow_up_date.strftime('%Y-%m-%d')}")
st.write(f"**Needs Invoice Resend:** {' Yes' if call.needs_invoice_resend else ' No'}")
st.write(f"**Customer Disputed:** {' Yes' if call.customer_disputed else ' No'}")
if call.dispute_reason:
st.write(f"**Dispute Reason:** {call.dispute_reason}")
# Transcript
st.markdown("#### 📝 Transcript")
if call.transcript:
st.text_area(
"Full conversation transcript",
call.transcript,
height=300,
key=f"transcript_{call.id}"
)
else:
st.info("No transcript available")
# Summary
st.markdown("#### 📄 Summary")
if call.summary:
st.info(call.summary)
else:
st.info("No summary available")
# Footer
st.markdown("---")
st.caption(" **Tip**: Use filters to narrow down calls by status, language, or sentiment. Download CSV for detailed analysis.")
if __name__ == "__main__":
main()
