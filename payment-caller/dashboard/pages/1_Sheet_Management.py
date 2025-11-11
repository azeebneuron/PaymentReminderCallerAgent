import sys
from pathlib import Path
# Setup project path
current_dir = Path(__file__).parent.parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
import streamlit as st
import pandas as pd
from datetime import datetime
from database.database import get_db
from database.models import Client, Invoice, PaymentStatus
from services.google_sheets import google_sheets_service
from config.settings import settings
# Page configuration
st.set_page_config(
page_title="Sheet Management",
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
.client-card {
background-color: #f8f9fa;
padding: 1.5rem;
border-radius: 8px;
margin-bottom: 1rem;
border: 1px solid #dee2e6;
}
.status-active {
color: #28a745;
font-weight: 600;
}
.status-inactive {
color: #dc3545;
font-weight: 600;
}
</style>
""", unsafe_allow_html=True)
def validate_sheet_access(sheet_id):
"""Validate service account has access to the Google Sheet."""
try:
sheet = google_sheets_service.get_sheet(sheet_id)
return True, f" Successfully connected to sheet: {sheet.title}", sheet.title
except Exception as e:
error_msg = str(e)
if "credentials" in error_msg.lower():
return False, " Service account credentials invalid. Check credentials file.", None
elif "permission" in error_msg.lower() or "access" in error_msg.lower():
return False, f" No access to sheet. Please share sheet with service account: {settings.google_sheets_credentials_file}", None
else:
return False, f" Error accessing sheet: {error_msg}", None
def preview_sheet_data(sheet_id):
"""Preview pending payments from the sheet."""
try:
pending_payments = google_sheets_service.get_pending_payments(sheet_id=sheet_id)
return pending_payments[:5] # Return first 5 for preview
except Exception as e:
st.error(f"Error fetching sheet data: {e}")
return []
def save_client_to_db(client_name, company_name, contact_number, sheet_id):
"""Save or update client in database."""
try:
with get_db() as db:
# Check if client with this contact already exists
existing_client = db.query(Client).filter(
Client.contact_number == contact_number
).first()
if existing_client:
# Update existing client
existing_client.client_name = client_name
existing_client.company_name = company_name
existing_client.google_sheet_id = sheet_id
existing_client.updated_at = datetime.utcnow()
message = f" Updated existing client: {client_name}"
else:
# Create new client
new_client = Client(
client_name=client_name,
company_name=company_name,
contact_number=contact_number,
google_sheet_id=sheet_id
)
db.add(new_client)
message = f" Added new client: {client_name}"
db.commit()
return True, message
except Exception as e:
return False, f" Error saving client: {str(e)}"
def delete_client(client_id):
"""Delete a client from the database."""
try:
with get_db() as db:
client = db.query(Client).filter(Client.id == client_id).first()
if client:
client_name = client.client_name
db.delete(client)
db.commit()
return True, f" Deleted client: {client_name}"
else:
return False, " Client not found"
except Exception as e:
return False, f" Error deleting client: {str(e)}"
def main():
"""Sheet Management page."""
st.markdown('<p class="main-header"> Sheet Management</p>', unsafe_allow_html=True)
st.markdown("Manage Google Sheets for different clients. Each client can have their own sheet with pending invoices.")
# Create tabs
tab1, tab2 = st.tabs([" Add New Client Sheet", " Manage Existing Clients"])
# TAB 1: Add New Client Sheet
with tab1:
st.markdown('<p class="section-header">Add New Client Sheet</p>', unsafe_allow_html=True)
with st.form("add_client_form"):
st.markdown("### Client Information")
col1, col2 = st.columns(2)
with col1:
client_name = st.text_input(
"Client Name *",
placeholder="e.g., Teknovace Coatings",
help="Name of the client/person"
)
contact_number = st.text_input(
"Contact Number *",
placeholder="+919999999999",
help="Mobile number with country code (e.g., +91XXXXXXXXXX)"
)
with col2:
company_name = st.text_input(
"Company Name",
placeholder="e.g., Teknovace Coatings Pvt Ltd",
help="Optional company name"
)
st.markdown("### Google Sheet Configuration")
sheet_id = st.text_input(
"Google Sheet ID *",
placeholder="1ABC...XYZ",
help="The Sheet ID from the Google Sheets URL"
)
st.info(" **How to find Sheet ID**: Open your Google Sheet and copy the ID from the URL: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`")
col1, col2 = st.columns(2)
with col1:
validate_btn = st.form_submit_button(" Validate Sheet Access", use_container_width=True)
with col2:
save_btn = st.form_submit_button(" Save Client", type="primary", use_container_width=True)
# Handle validation
if validate_btn:
if not sheet_id:
st.error(" Please enter a Sheet ID")
else:
with st.spinner("Validating sheet access..."):
is_valid, message, sheet_title = validate_sheet_access(sheet_id)
if is_valid:
st.success(message)
# Show preview
st.markdown("### Sheet Data Preview")
with st.spinner("Loading preview..."):
preview_data = preview_sheet_data(sheet_id)
if preview_data:
st.write(f"**Found {len(preview_data)} pending invoice(s) (showing first 5):**")
preview_df = pd.DataFrame([
{
'Client': p['client_name'],
'Invoice ID': p['invoice_id'],
'Amount Due': f"₹{p['amount_due']:,.2f}",
'Due Date': p['due_date'].strftime('%Y-%m-%d') if p['due_date'] else 'N/A',
'Contact': p['contact_number']
}
for p in preview_data
])
st.dataframe(preview_df, use_container_width=True)
# Store validation state
st.session_state['validated_sheet_id'] = sheet_id
st.session_state['sheet_title'] = sheet_title
else:
st.warning(" No pending payments found in this sheet")
else:
st.error(message)
st.info("**Troubleshooting:**\n1. Make sure you've shared the sheet with the service account email\n2. Check that the sheet ID is correct\n3. Verify the sheet has the expected structure")
# Handle save
if save_btn:
# Validation
errors = []
if not client_name:
errors.append("Client Name is required")
if not contact_number:
errors.append("Contact Number is required")
if not sheet_id:
errors.append("Google Sheet ID is required")
# Validate contact number format
if contact_number and not contact_number.startswith('+'):
errors.append("Contact number must include country code (e.g., +91...)")
if errors:
for error in errors:
st.error(f" {error}")
else:
# Verify sheet access before saving
with st.spinner("Verifying sheet access..."):
is_valid, message, sheet_title = validate_sheet_access(sheet_id)
if not is_valid:
st.error(message)
st.error(" Cannot save client without valid sheet access")
else:
# Save to database
success, save_message = save_client_to_db(
client_name=client_name,
company_name=company_name or client_name,
contact_number=contact_number,
sheet_id=sheet_id
)
if success:
st.success(save_message)
st.balloons()
# Clear form (by clearing session state)
if 'validated_sheet_id' in st.session_state:
del st.session_state['validated_sheet_id']
st.info(" Client saved! You can now make calls to this client from the 'Make Calls' page.")
else:
st.error(save_message)
# TAB 2: Manage Existing Clients
with tab2:
st.markdown('<p class="section-header">Existing Clients</p>', unsafe_allow_html=True)
# Load clients
with get_db() as db:
clients = db.query(Client).all()
client_data = []
for client in clients:
# Count pending invoices
pending_count = db.query(Invoice).filter(
Invoice.client_id == client.id,
Invoice.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE])
).count()
client_data.append({
'id': client.id,
'name': client.client_name,
'company': client.company_name,
'contact': client.contact_number,
'sheet_id': client.google_sheet_id,
'created': client.created_at,
'pending_invoices': pending_count
})
if not client_data:
st.info(" No clients added yet. Add your first client in the 'Add New Client Sheet' tab.")
else:
st.write(f"**Total Clients:** {len(client_data)}")
# Show clients
for client in client_data:
with st.container():
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
st.markdown(
f"""
<div class="client-card">
<h3 style="margin: 0 0 0.5rem 0;">{client['name']}</h3>
<p style="margin: 0; color: #666;">
{client['company']}<br>
{client['contact']}<br>
{client['pending_invoices']} pending invoice(s)<br>
Added: {client['created'].strftime('%Y-%m-%d')}
</p>
<p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #999;">
Sheet ID: {client['sheet_id'][:30]}...
</p>
</div>
""",
unsafe_allow_html=True
)
with col2:
# Test connection
if st.button(" Test", key=f"test_{client['id']}", use_container_width=True):
with st.spinner("Testing..."):
is_valid, message, _ = validate_sheet_access(client['sheet_id'])
if is_valid:
st.success(" Connected")
else:
st.error(" Failed")
st.caption(message)
with col3:
# Delete button
if st.button(" Delete", key=f"delete_{client['id']}", use_container_width=True):
# Show confirmation dialog
st.session_state[f'confirm_delete_{client["id"]}'] = True
# Show delete confirmation if needed
if st.session_state.get(f'confirm_delete_{client["id"]}', False):
st.warning(f" Are you sure you want to delete **{client['name']}**?")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
if st.button(" Yes, Delete", key=f"confirm_yes_{client['id']}"):
success, message = delete_client(client['id'])
if success:
st.success(message)
del st.session_state[f'confirm_delete_{client["id"]}']
st.rerun()
else:
st.error(message)
with col2:
if st.button(" Cancel", key=f"confirm_no_{client['id']}"):
del st.session_state[f'confirm_delete_{client["id"]}']
st.rerun()
st.markdown("---")
# Bulk actions
st.markdown("### Bulk Actions")
col1, col2 = st.columns(2)
with col1:
if st.button(" Test All Connections", use_container_width=True):
st.markdown("#### Connection Test Results")
for client in client_data:
with st.spinner(f"Testing {client['name']}..."):
is_valid, message, _ = validate_sheet_access(client['sheet_id'])
if is_valid:
st.success(f" {client['name']}: Connected")
else:
st.error(f" {client['name']}: {message}")
with col2:
if st.button(" Export Client List", use_container_width=True):
# Create DataFrame
export_df = pd.DataFrame([
{
'Client Name': c['name'],
'Company': c['company'],
'Contact Number': c['contact'],
'Google Sheet ID': c['sheet_id'],
'Pending Invoices': c['pending_invoices'],
'Added Date': c['created'].strftime('%Y-%m-%d')
}
for c in client_data
])
csv = export_df.to_csv(index=False)
st.download_button(
label=" Download CSV",
data=csv,
file_name=f"clients_{datetime.now().strftime('%Y%m%d')}.csv",
mime="text/csv",
use_container_width=True
)
# Footer
st.markdown("---")
st.caption(" **Tip**: Share your Google Sheet with the service account email to grant access.")
if __name__ == "__main__":
main()
