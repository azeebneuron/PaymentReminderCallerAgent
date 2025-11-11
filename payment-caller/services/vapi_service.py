"""
Vapi.ai integration service for making outbound calls.
"""
import asyncio
import httpx
from typing import Dict, Optional, Any
from datetime import datetime, date
from config.settings import settings, voice_config
from config.prompts import PAYMENT_REMINDER_SYSTEM_PROMPT
from utils.logger import logger
import phonenumbers


class VapiService:
    """Service for interacting with Vapi.ai API."""
    
    BASE_URL = "https://api.vapi.ai"
    
    def __init__(self):
        self.headers = settings.get_vapi_headers()
    
    def create_assistant_config(
        self, 
        client_name: str, 
        company_name: str,
        invoice_id: str, 
        amount_due: float, 
        due_date: date
    ) -> Dict[str, Any]:
        """
        Create transient assistant configuration for the call.
        """
        from config.prompts import get_payment_reminder_prompt
        
        # Format amounts
        amount_formatted = f"₹{amount_due:,.2f}"
        due_date_formatted = due_date.strftime("%d %B %Y")
        
        # Natural first message in Hindi
        first_message = (
            f"Namaste! Main Contigo Solutions se bol rahi hoon. "
            f"Kya aap abhi 2-3 minute baat kar sakte hain?"
        )
        
        # Prepare keywords with proper formatting
        # Format: "keyword" or "keyword:boost_value"
        # Clean and format each keyword properly
        keywords = []

        # Start with base keywords
        base_keywords = ["Contigo", "Solutions", "invoice", "payment"]

        # Add client/company specific keywords only if they exist and are valid
        if client_name:
            # Extract meaningful words from client name
            name_words = client_name.split()
            for word in name_words:
                cleaned = ''.join(c for c in word if c.isalpha())
                if cleaned and len(cleaned) >= 3:
                    base_keywords.append(cleaned)

        if company_name:
            # Extract meaningful words from company name
            company_words = company_name.split()
            for word in company_words:
                cleaned = ''.join(c for c in word if c.isalpha())
                if cleaned and len(cleaned) >= 3:
                    base_keywords.append(cleaned)

        # Clean and format each keyword
        for kw in base_keywords:
            # Only add valid keywords (alphabetic characters only, no numbers or special chars)
            cleaned_kw = ''.join(c for c in kw if c.isalpha())
            if cleaned_kw and len(cleaned_kw) >= 3:  # At least 3 characters
                # Use integer boost value (Vapi requires integers, not floats)
                keywords.append(f"{cleaned_kw}:2")
        
        return {
            # Cartesia Voice (Hindi/Hinglish)
            "voice": {
                "provider": "cartesia",
                "voiceId": "28ca2041-5dda-42df-8123-f58ea9c3da00",  # Ananya - Hindi female
                "language": "hi",  # Hindi language
            },
            
            # Deepgram Transcriber for Hindi
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "hi",  # Hindi transcription
                "smartFormat": True,
                "keywords": keywords  # Properly formatted keywords
            },
            
            # LLM Configuration
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "system",
                        "content": get_payment_reminder_prompt(
                            client_name=client_name,
                            company_name=company_name,
                            invoice_id=invoice_id,
                            amount_due=amount_due,
                            due_date=due_date
                        )
                    }
                ]
            },
            
            # First message
            "firstMessage": first_message,
            
            # End call message
            "endCallMessage": f"Thank you {client_name} ji. Dhanyavaad!",
            
            # Server configuration
            "server": {
                "url": settings.webhook_url,
                "timeoutSeconds": 30
            },
            
            # Server messages
            "serverMessages": [
                "end-of-call-report",
                "status-update",
                "transcript",
                "hang",
                "function-call"
            ],
            
            # Call settings
            "recordingEnabled": True,
            "maxDurationSeconds": settings.max_call_duration_seconds,
            "silenceTimeoutSeconds": 30,
            "endCallFunctionEnabled": True,
            
            # Background sound (optional - makes it feel more natural)
            "backgroundSound": "office",  # subtle office ambiance
        }
    
    def format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number to E.164 format (+919876543210).
        
        Args:
            phone_number: Phone number in any format
            
        Returns:
            Phone number in E.164 format
        """
        try:
            # Parse phone number (default region: India)
            parsed = phonenumbers.parse(phone_number, "IN")
            
            # Format to E.164
            formatted = phonenumbers.format_number(
                parsed, 
                phonenumbers.PhoneNumberFormat.E164
            )
            
            return formatted
        except Exception as e:
            logger.warning(f"Error formatting phone number {phone_number}: {e}")
            # If parsing fails, assume it's already formatted or add +91
            if not phone_number.startswith("+"):
                return f"+91{phone_number}"
            return phone_number
    
    async def make_outbound_call(
        self,
        client_name: str,
        company_name: str,
        contact_number: str,
        invoice_id: str,
        amount_due: float,
        due_date: date
    ) -> Optional[str]:
        """
        Make an outbound call via Vapi API.
        
        Args:
            client_name: Client name
            company_name: Company name
            contact_number: Contact number
            invoice_id: Invoice ID
            amount_due: Amount due
            due_date: Due date
            
        Returns:
            Vapi call ID if successful, None otherwise
        """
        try:
            # Format phone number
            formatted_number = self.format_phone_number(contact_number)
            
            # Create assistant config
            assistant_config = self.create_assistant_config(
                client_name=client_name,
                company_name=company_name,
                invoice_id=invoice_id,
                amount_due=amount_due,
                due_date=due_date
            )
            
            # Prepare payload
            payload = {
                "assistant": assistant_config,
                "phoneNumberId": settings.vapi_phone_number_id,
                "customer": {
                    "number": formatted_number,
                    "numberE164CheckEnabled": False
                }
            }
            
            # Log the payload for debugging (remove in production)
            logger.debug(f"Call payload: {payload}")
            
            # Make API call
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/call/phone",
                    json=payload,
                    headers=self.headers
                )
            
            if response.status_code == 201:
                call_data = response.json()
                logger.info(f"Call created successfully. Call ID: {call_data.get('id')}")
                return call_data.get("id")
            elif response.status_code == 429:  # Rate limited
                logger.warning("Rate limited by Vapi API")
                await asyncio.sleep(5)
                return None
            elif response.status_code == 401:  # Auth error
                logger.error("Invalid Vapi API key")
                raise ValueError("Authentication failed")
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
        except httpx.TimeoutException:
            logger.error("Vapi API timeout")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    async def get_call_status(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get call status from Vapi.
        
        Args:
            call_id: Vapi call ID
            
        Returns:
            Call status dict or None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/call/{call_id}",
                    headers=self.headers
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get call status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting call status: {e}")
            return None


# Global instance
vapi_service = VapiService()