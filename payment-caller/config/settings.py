"""
Centralized configuration settings for the AI Payment Caller application.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import time


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Vapi Configuration
    vapi_api_key: str
    vapi_phone_number_id: str
    vapi_webhook_secret: Optional[str] = None

    # Gemini Configuration
    gemini_api_key: str

    # Database
    database_url: str = f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(__file__)), 'payment_caller.db')}"

    # Google Sheets
    google_sheets_credentials_file: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
    google_sheet_id: str
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"
    webhook_url: str = "http://localhost:8000/vapi/webhook"
    
    # Scheduler
    daily_run_time: str = "09:00"
    timezone: str = "Asia/Kolkata"
    
    # Call Configuration
    max_call_duration_seconds: int = 300
    call_retry_attempts: int = 2
    call_rate_limit_per_minute: int = 10
    business_hours_start: str = "10:00"
    business_hours_end: str = "19:00"
    
    # Dashboard
    dashboard_port: int = 8501
    dashboard_title: str = "Payment Caller Dashboard"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # Environment
    environment: str = "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def business_start_time(self) -> time:
        """Convert business hours start to time object."""
        hour, minute = map(int, self.business_hours_start.split(":"))
        return time(hour=hour, minute=minute)
    
    @property
    def business_end_time(self) -> time:
        """Convert business hours end to time object."""
        hour, minute = map(int, self.business_hours_end.split(":"))
        return time(hour=hour, minute=minute)
    
    def get_vapi_headers(self) -> dict:
        """Get headers for Vapi API requests."""
        return {
            "Authorization": f"Bearer {self.vapi_api_key}",
            "Content-Type": "application/json"
        }


# Global settings instance
settings = Settings()

# Voice Configuration
class VoiceConfig:
    VOICE = {
        "provider": "cartesia",
        "voiceId": "28ca2041-5dda-42df-8123-f58ea9c3da00",  # Ananya - Hindi female voice
        # Other great Hindi voices:
        # "248be419-c632-4f23-adf1-5324ed7dbf1d" - Aadhya (Hindi female)
        # "e13cae5c-ec59-4f71-b0a6-266df3c9a06a" - Ananya (Hindi female)
        # "a167e0f3-df7e-4d52-a9c3-f949145efdab" - Apoorva (Hindi female)
        # "79a125e8-cd45-4c13-8a67-188112f4dd22" - Indian Male voice
        # For Hinglish: "f9836c6e-a0bd-460e-9d3c-f7299fa60f94" - Hinglish female
    }

    # Cartesia Transcriber (STT)
    TRANSCRIBER = {
        "provider": "deepgram",
        "model": "nova-2",
        "language": "hi",  # Hindi
        "smartFormat": True,
        "keywords": ["Contigo Solutions", "invoice", "payment", "rupees"]
    }

    # LLM Model Configuration
    MODEL = {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.7
    }


voice_config = VoiceConfig()