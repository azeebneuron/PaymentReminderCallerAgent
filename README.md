# AI Payment Caller System

An automated payment reminder system powered by AI voice agents for handling payment follow-ups via phone calls.

## Overview

The AI Payment Caller System automates the process of making payment reminder calls to clients with pending invoices. It integrates with Google Sheets for data management, uses Vapi.ai for voice calls, and employs Gemini AI for intelligent call analysis and response parsing.

### Key Features

- **Multilingual AI Voice Agent** - Speaks Hindi, English, and Marathi with natural conversation flow
- **Automated Daily Calls** - Scheduled reminders for pending payments during business hours
- **Google Sheets Integration** - Seamless sync with existing payment tracking spreadsheets
- **Multi-Client Support** - Manage multiple clients with separate Google Sheets
- **Real-time Dashboard** - Web-based dashboard for monitoring calls and managing clients
- **Smart Call Analysis** - AI-powered analysis of call outcomes and automatic sheet updates
- **Call Recording & Transcription** - Complete audit trail of all conversations
- **Manual & Automated Triggers** - On-demand calls or scheduled automation

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Google Sheets Setup](#google-sheets-setup)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

## Prerequisites

Before setting up the system, ensure you have:

- **Python 3.11 or higher**
- **Vapi.ai Account** - Sign up at [vapi.ai](https://vapi.ai) and obtain:
  - API Key
  - Phone Number ID
- **Google Gemini API Key** - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Google Cloud Service Account** - For Google Sheets API access
- **Public URL for Webhooks** - Use ngrok for local development or your domain for production

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd DevHubCallerAgent/payment-caller
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and configure the following **required** variables:

#### Vapi Configuration (Required)
```bash
VAPI_API_KEY=your_vapi_api_key_here
VAPI_PHONE_NUMBER_ID=your_vapi_phone_number_id_here
```
Get these from [Vapi Dashboard](https://vapi.ai/dashboard)

#### Gemini AI Configuration (Required)
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```
Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

#### Google Sheets Configuration (Required)
```bash
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id_here
```

#### Webhook Configuration (Required for Production)
```bash
# For local development with ngrok:
WEBHOOK_URL=https://abc123.ngrok-free.app/vapi/webhook

# For production:
WEBHOOK_URL=https://yourdomain.com/vapi/webhook
```

#### Optional Configuration

All other variables have sensible defaults. Common ones to customize:

```bash
# Business hours for making calls (24-hour format)
BUSINESS_HOURS_START=10:00
BUSINESS_HOURS_END=19:00

# Scheduler - daily automated call time
DAILY_RUN_TIME=09:00
TIMEZONE=Asia/Kolkata

# Call settings
MAX_CALL_DURATION_SECONDS=300
CALL_RETRY_ATTEMPTS=2
CALL_RATE_LIMIT_PER_MINUTE=10
```

See `.env.example` for complete list of configuration options.

### 2. Database Setup

The system uses SQLite by default for development. The database is automatically created on first run.

For production with PostgreSQL:
```bash
DATABASE_URL=postgresql://username:password@host:5432/payment_caller
```

## Google Sheets Setup

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable **Google Sheets API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in service account details
   - Click "Create and Continue"
   - Skip granting roles (click "Continue")
   - Click "Done"
5. Create and Download Key:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Click "Create"
6. Save the downloaded JSON file as `credentials.json` in the `payment-caller` directory

### 2. Prepare Your Google Sheet

Your Google Sheet should have the following columns:

| Required Columns | Description |
|-----------------|-------------|
| Date | Invoice date |
| Invoice ID | Unique invoice identifier |
| Client Name | Customer name |
| Contact Number | Phone number with country code (e.g., +919876543210) |
| Pending Amount | Outstanding amount |
| Due Date | Payment due date |
| Payment Status | Current status (PENDING, PAID, OVERDUE, etc.) |

Optional columns:
- Company Name
- Email
- Address
- Notes

### 3. Share Sheet with Service Account

1. Open your `credentials.json` file
2. Copy the `client_email` value (looks like `xxxx@yyyy.iam.gserviceaccount.com`)
3. Open your Google Sheet
4. Click "Share" button
5. Paste the service account email
6. Give it **Editor** permissions
7. Click "Share"

### 4. Get Your Sheet ID

The Sheet ID is in your Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/[YOUR_SHEET_ID]/edit
```

Copy the ID between `/d/` and `/edit` and add it to your `.env` file.

## Running the Application

The system consists of two components that run simultaneously:

### 1. Start the API Server (Terminal 1)

```bash
cd payment-caller
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API server will be available at `http://localhost:8000`

### 2. Start the Dashboard (Terminal 2)

```bash
cd payment-caller
source venv/bin/activate
streamlit run dashboard/app.py --server.port 8501
```

The dashboard will be available at `http://localhost:8501`

### 3. Setup Webhook URL (For Local Development)

If testing locally, use ngrok to expose your webhook:

```bash
# In Terminal 3
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok-free.app`) and update your `.env`:
```bash
WEBHOOK_URL=https://abc123.ngrok-free.app/vapi/webhook
```

Restart the API server after updating the webhook URL.

## Usage

### Dashboard Interface

Access the dashboard at `http://localhost:8501` to:

1. **Home Page** - View daily summary, alerts, and active clients
2. **Sheet Management** - Add and manage client Google Sheets
3. **Make Calls** - Manually trigger calls to specific clients
4. **Call Logs** - View detailed call history and transcripts
5. **Pending Invoices** - Monitor outstanding payments
6. **Settings** - Configure system parameters

### Adding Your First Client

1. Go to **Sheet Management** page
2. Click on "Add New Client Sheet" tab
3. Fill in:
   - Client Name (required)
   - Contact Number with country code (required)
   - Company Name (optional)
   - Google Sheet ID (required)
4. Click "Validate Sheet Access" to test connection
5. Review the preview of pending invoices
6. Click "Save Client"

### Making Manual Calls

1. Go to **Make Calls** page
2. Select a client from the dropdown
3. Choose specific invoices or select all
4. Click "Start Calling"
5. Monitor call progress in real-time

### Automated Calls

The system automatically processes calls based on the schedule in `.env`:

```bash
DAILY_RUN_TIME=09:00  # Calls start at 9:00 AM
TIMEZONE=Asia/Kolkata
```

Calls are only made during configured business hours.

## API Documentation

### Webhook Endpoints

**POST `/vapi/webhook`**
- Receives call status updates from Vapi
- Processes call transcripts with AI
- Updates Google Sheets with results

### Call Management

**POST `/calls/trigger`**
```json
{
  "client_id": 1,
  "invoice_ids": ["INV-001", "INV-002"]
}
```

**POST `/calls/process-all`**
- Processes all pending payments for all clients

**GET `/calls/`**
- List all call logs with optional filters

**GET `/calls/{call_id}`**
- Get detailed call information

### Reports

**GET `/reports/daily`**
- Daily call statistics

**GET `/reports/weekly`**
- Weekly performance report

**GET `/reports/pending-invoices`**
- Summary of all pending invoices

**GET `/reports/client-history/{client_id}`**
- Call history for specific client

## Project Structure

```
payment-caller/
├── api/                          # FastAPI application
│   ├── main.py                   # Application entry point
│   └── routes/                   # API route handlers
│       ├── vapi_routes.py        # Vapi webhook handlers
│       ├── call_routes.py        # Call management
│       └── report_routes.py      # Reporting endpoints
├── config/                       # Configuration
│   ├── settings.py               # Application settings
│   └── prompts.py                # AI conversation prompts
├── database/                     # Database layer
│   ├── database.py               # Database connection
│   └── models.py                 # SQLAlchemy models
├── services/                     # Business logic
│   ├── vapi_service.py           # Vapi API integration
│   ├── google_sheets.py          # Google Sheets integration
│   ├── call_orchestrator.py     # Main call workflow
│   ├── response_parser.py        # AI response parsing
│   └── scheduler_service.py      # Scheduled tasks
├── dashboard/                    # Streamlit dashboard
│   ├── app.py                    # Main dashboard page
│   └── pages/                    # Dashboard pages
│       ├── 1_Sheet_Management.py
│       ├── 2_Make_Calls.py
│       ├── 3_Call_Logs.py
│       ├── 4_Pending_Invoices.py
│       └── 5_Settings.py
├── scripts/                      # Utility scripts
│   ├── manage_clients.py         # Client management CLI
│   ├── migrate_add_sheet_id.py   # Database migration
│   └── quick_demo_call.py        # Test call script
├── utils/                        # Utilities
│   └── logger.py                 # Logging configuration
├── credentials.json              # Google service account (you create this)
├── .env                          # Environment variables (you create this)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
└── payment_caller.db             # SQLite database (auto-created)
```

## Troubleshooting

### Issue: Database Connection Error

**Solution:**
- Check `DATABASE_URL` in `.env`
- For SQLite, ensure the directory is writable
- For PostgreSQL, verify server is running and credentials are correct

### Issue: Google Sheets Not Syncing

**Solution:**
1. Verify `credentials.json` exists in the project root
2. Check that service account email has Editor access to the sheet
3. Confirm `GOOGLE_SHEET_ID` is correct in `.env`
4. Test connection using "Validate Sheet Access" in dashboard

### Issue: Vapi Calls Failing

**Solution:**
1. Verify `VAPI_API_KEY` is correct
2. Check phone number format includes country code (e.g., +919876543210)
3. Ensure `VAPI_PHONE_NUMBER_ID` is valid
4. Check Vapi dashboard for account status and balance

### Issue: Webhooks Not Working

**Solution:**
1. Ensure webhook URL is publicly accessible (test with curl)
2. For local development, use ngrok and update `.env` with the ngrok URL
3. Check firewall settings
4. Verify webhook URL is configured in Vapi dashboard (if manual setup)
5. Check API server logs for incoming requests

### Issue: No Calls Being Made

**Solution:**
1. Verify current time is within business hours (check `BUSINESS_HOURS_START` and `BUSINESS_HOURS_END`)
2. Ensure pending invoices exist in Google Sheet
3. Check contact numbers are in correct format (+country code)
4. Verify Vapi API key is valid and account has credits
5. Check logs at `logs/app.log` for errors

### Viewing Logs

```bash
# Real-time log monitoring
tail -f logs/app.log

# View with debug level
# Set in .env: LOG_LEVEL=DEBUG
```

## Production Deployment

### Deployment Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Configure PostgreSQL database URL
- [ ] Set up proper `WEBHOOK_URL` with your domain
- [ ] Configure firewall to allow webhook traffic
- [ ] Set up SSL/TLS for API server
- [ ] Configure process manager (systemd, supervisor, or PM2)
- [ ] Set up log rotation
- [ ] Configure backup strategy for database
- [ ] Set appropriate `LOG_LEVEL` (WARNING or ERROR for production)
- [ ] Secure `.env` and `credentials.json` files (chmod 600)

### Using systemd (Linux)

Create `/etc/systemd/system/payment-caller-api.service`:

```ini
[Unit]
Description=Payment Caller API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/payment-caller
Environment="PATH=/path/to/payment-caller/venv/bin"
ExecStart=/path/to/payment-caller/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/payment-caller-dashboard.service`:

```ini
[Unit]
Description=Payment Caller Dashboard
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/payment-caller
Environment="PATH=/path/to/payment-caller/venv/bin"
ExecStart=/path/to/payment-caller/venv/bin/streamlit run dashboard/app.py --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable payment-caller-api
sudo systemctl enable payment-caller-dashboard
sudo systemctl start payment-caller-api
sudo systemctl start payment-caller-dashboard
```

### Using Docker (Alternative)

A `Dockerfile` can be created for containerized deployment. This is recommended for cloud platforms.

### Cloud Platform Options

- **Railway.app** - Easy deployment with GitHub integration
- **Render** - Free tier available for testing
- **DigitalOcean App Platform** - Simple scalability
- **AWS/GCP/Azure** - For enterprise deployments

## Security Considerations

- **Never commit** `.env` or `credentials.json` to version control
- Store sensitive credentials in environment variables or secrets manager
- Use HTTPS for all webhook endpoints
- Implement API authentication for production use
- Regularly rotate API keys and service account credentials
- Restrict service account permissions to minimum required
- Set up monitoring and alerts for suspicious activity
- Keep dependencies updated (`pip install --upgrade -r requirements.txt`)

## Support and Maintenance

### Monitoring

- Check `logs/app.log` regularly
- Monitor Vapi dashboard for call statistics
- Review database size and performance
- Track Google Sheets API quota usage

### Regular Maintenance

- Backup database regularly
- Archive old call logs (>90 days)
- Review and update AI prompts for better results
- Update dependencies for security patches
- Test webhook connectivity periodically

## License

MIT License - See LICENSE file for details.

---

**Need Help?** Check the logs first (`logs/app.log`), then review this README. For API-specific issues, consult the Vapi or Google Sheets documentation.
