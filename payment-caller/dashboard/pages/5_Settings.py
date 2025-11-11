import sys
from pathlib import Path
# Setup project path
current_dir = Path(__file__).parent.parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
import streamlit as st
import os
from config.settings import settings
# Page configuration
st.set_page_config(
page_title="Settings",
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
.config-card {
background-color: #f8f9fa;
padding: 1.5rem;
border-radius: 8px;
margin-bottom: 1rem;
border: 1px solid #dee2e6;
}
.status-ok {
color: #28a745;
font-weight: 600;
}
.status-error {
color: #dc3545;
font-weight: 600;
}
</style>
""", unsafe_allow_html=True)
def check_file_exists(filepath):
"""Check if a file exists."""
return os.path.exists(filepath)
def main():
"""Settings page."""
st.markdown('<p class="main-header"> Settings & Configuration</p>', unsafe_allow_html=True)
st.markdown("View and manage system configuration, API keys, and service status.")
# System Status
st.markdown('<p class="section-header"> System Status</p>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
st.markdown("#### Service Health")
# Check Google Sheets credentials
sheets_creds_exist = check_file_exists(settings.google_sheets_credentials_file)
if sheets_creds_exist:
st.markdown(" **Google Sheets**: <span class='status-ok'>Connected</span>", unsafe_allow_html=True)
else:
st.markdown(" **Google Sheets**: <span class='status-error'>Credentials Missing</span>", unsafe_allow_html=True)
# Check database
db_exists = check_file_exists(settings.database_url.replace('sqlite:///', ''))
if db_exists:
st.markdown(" **Database**: <span class='status-ok'>Connected</span>", unsafe_allow_html=True)
else:
st.markdown(" **Database**: <span class='status-error'>Not Found</span>", unsafe_allow_html=True)
# Check Vapi API key
if settings.vapi_api_key and settings.vapi_api_key != "":
st.markdown(" **Vapi API**: <span class='status-ok'>Configured</span>", unsafe_allow_html=True)
else:
st.markdown(" **Vapi API**: <span class='status-error'>Not Configured</span>", unsafe_allow_html=True)
# Check Gemini API key
if settings.gemini_api_key and settings.gemini_api_key != "":
st.markdown(" **Gemini AI**: <span class='status-ok'>Configured</span>", unsafe_allow_html=True)
else:
st.markdown(" **Gemini AI**: <span class='status-error'>Not Configured</span>", unsafe_allow_html=True)
with col2:
st.markdown("#### Webhook Status")
if settings.webhook_url:
st.write(f"**URL**: {settings.webhook_url}")
st.caption("Make sure this URL is accessible by Vapi")
else:
st.error(" Webhook URL not configured")
# Configuration Details
st.markdown('<p class="section-header"> Current Configuration</p>', unsafe_allow_html=True)
config_tabs = st.tabs([" Call Settings", "🌐 API Settings", " Google Sheets", " Business Hours"])
# Call Settings Tab
with config_tabs[0]:
st.markdown("#### Call Configuration")
col1, col2 = st.columns(2)
with col1:
st.info(f"**Call Rate Limit**: {settings.call_rate_limit_per_minute} calls/minute")
st.info(f"**Vapi Phone Number**: {settings.vapi_phone_number_id}")
st.info(f"**Max Call Duration**: {settings.max_call_duration_seconds} seconds")
with col2:
st.info(f"**Call Retry Attempts**: {settings.call_retry_attempts} attempts")
st.info(f"**Rate Limit Delay**: {60 / settings.call_rate_limit_per_minute:.1f} seconds")
st.info(f"**Business Hours**: {settings.business_hours_start} - {settings.business_hours_end}")
st.markdown("---")
st.warning(" **Note**: These settings are configured in the `.env` file. To modify them, update the `.env` file and restart the application.")
# API Settings Tab
with config_tabs[1]:
st.markdown("#### API Keys & Credentials")
st.warning("🔒 **Security Warning**: Never share your API keys publicly!")
col1, col2 = st.columns(2)
with col1:
st.markdown("**Vapi API Key**")
if settings.vapi_api_key:
masked_vapi = settings.vapi_api_key[:10] + "..." + settings.vapi_api_key[-4:]
st.code(masked_vapi)
else:
st.error("Not configured")
with col2:
st.markdown("**Gemini API Key**")
if settings.gemini_api_key:
masked_gemini = settings.gemini_api_key[:10] + "..." + settings.gemini_api_key[-4:]
st.code(masked_gemini)
else:
st.error("Not configured")
st.markdown("---")
st.markdown("**Webhook URL**")
if settings.webhook_url:
st.code(settings.webhook_url)
else:
st.error("Not configured")
# Google Sheets Tab
with config_tabs[2]:
st.markdown("#### Google Sheets Configuration")
col1, col2 = st.columns(2)
with col1:
st.info(f"**Credentials File**: {settings.google_sheets_credentials_file}")
if check_file_exists(settings.google_sheets_credentials_file):
st.success(" Credentials file found")
else:
st.error(" Credentials file not found")
with col2:
st.info(f"**Default Sheet ID**: {settings.google_sheet_id[:20]}...")
st.markdown("---")
st.markdown("#### Service Account Email")
if check_file_exists(settings.google_sheets_credentials_file):
try:
import json
with open(settings.google_sheets_credentials_file, 'r') as f:
creds = json.load(f)
service_account_email = creds.get('client_email', 'Not found')
st.code(service_account_email)
st.caption(" Share your Google Sheets with this email address to grant access.")
except Exception as e:
st.error(f"Error reading credentials: {e}")
else:
st.warning("Credentials file not found")
# Business Hours Tab
with config_tabs[3]:
st.markdown("#### Business Hours Configuration")
col1, col2 = st.columns(2)
with col1:
st.info(f"**Start Time**: {settings.business_start_time}")
st.info(f"**Timezone**: {settings.timezone}")
with col2:
st.info(f"**End Time**: {settings.business_end_time}")
st.markdown("---")
from datetime import datetime
import pytz
tz = pytz.timezone(settings.timezone)
current_time = datetime.now(tz).time()
is_business_hours = settings.business_start_time <= current_time <= settings.business_end_time
if is_business_hours:
st.success(f" **Currently within business hours** (Current time: {current_time.strftime('%H:%M:%S')})")
else:
st.warning(f" **Outside business hours** (Current time: {current_time.strftime('%H:%M:%S')})")
st.info(" Calls will only be made during business hours to avoid disturbing customers outside working times.")
# Database Information
st.markdown('<p class="section-header"> Database Information</p>', unsafe_allow_html=True)
from database.database import get_db
from database.models import Client, Invoice, CallLog
with get_db() as db:
client_count = db.query(Client).count()
invoice_count = db.query(Invoice).count()
call_count = db.query(CallLog).count()
col1, col2, col3 = st.columns(3)
with col1:
st.metric("Total Clients", client_count)
with col2:
st.metric("Total Invoices", invoice_count)
with col3:
st.metric("Total Calls", call_count)
st.info(f"**Database Location**: {settings.database_url}")
# Actions
st.markdown('<p class="section-header">🔧 Actions</p>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
if st.button(" Reload Configuration", use_container_width=True):
st.rerun()
with col2:
if st.button(" View Database Stats", use_container_width=True):
st.info("Database statistics shown above")
with col3:
if st.button("📖 View Documentation", use_container_width=True):
st.markdown("""
### 📖 Quick Guide
**1. Adding Clients**:
- Go to Sheet Management page
- Enter client details and Google Sheet ID
- Validate sheet access
- Save client
**2. Making Calls**:
- Go to Make Calls page
- Select client
- Choose call mode (All, Select, or Schedule)
- Preview and confirm
**3. Viewing Results**:
- Call Logs: View all call history with filters
- Pending Invoices: See outstanding payments by priority
**4. Google Sheets Integration**:
- Share your sheet with service account email
- Ensure sheet has required columns
- System auto-updates after each call
""")
# Footer
st.markdown("---")
st.caption(" **Tip**: Keep your API keys secure and never commit them to version control. Use environment variables (.env file) for configuration.")
if __name__ == "__main__":
main()
