"""
Response parser service to analyze call transcripts using Gemini.
"""
import json
import re
from typing import Dict, Optional
from datetime import datetime, timedelta, date
import google.generativeai as genai
from config.settings import settings
from config.prompts import RESPONSE_CLASSIFICATION_PROMPT
from utils.logger import logger


class ResponseParser:
    """Service to parse call transcripts and extract structured information."""
    
    def __init__(self):
        try:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            raise
    
    def _clean_json_response(self, text: str) -> str:
        """Extracts JSON string from markdown or plain text."""
        # Find JSON block wrapped in markdown
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        
        # Find a bare JSON object
        match = re.search(r'(\{.*?\})', text, re.DOTALL)
        if match:
            return match.group(1)
            
        logger.warning("Could not find JSON in Gemini response")
        return "{}"

    def parse_call_outcome(
        self, 
        transcript: str, 
        summary: Optional[str] = None
    ) -> Dict:
        """
        Parse call transcript to extract structured information using Gemini.
        Args:
            transcript: Full call transcript
            summary: Optional call summary from Vapi
            
        Returns:
            Dict with parsed information
        """
        try:
            # Create prompt
            prompt = RESPONSE_CLASSIFICATION_PROMPT.format(
                transcript=transcript,
                summary=summary or "Not provided"
            )
            
            # Call Gemini
            response = self.model.generate_content(prompt)
            
            # Clean and parse JSON response
            json_string = self._clean_json_response(response.text)
            result = json.loads(json_string)
            
            # Convert date strings to date objects
            if result.get('payment_promise_date'):
                try:
                    result['payment_promise_date'] = datetime.strptime(
                        result['payment_promise_date'], 
                        '%Y-%m-%d'
                    ).date()
                except:
                    result['payment_promise_date'] = None
            
            if result.get('next_follow_up_date'):
                try:
                    result['next_follow_up_date'] = datetime.strptime(
                        result['next_follow_up_date'], 
                        '%Y-%m-%d'
                    ).date()
                except:
                    result['next_follow_up_date'] = None
            
            logger.info("Successfully parsed call outcome with Gemini")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing call outcome with Gemini: {e}")
            
            # Return default structure on error
            return {
                "payment_status": "other",
                "payment_promised": False,
                "payment_promise_date": None,
                "needs_invoice_resend": False,
                "customer_disputed": False,
                "dispute_reason": None,
                "next_follow_up_date": None,
                "language_detected": "unknown",
                "customer_sentiment": "neutral",
                "notes": f"Error parsing: {str(e)}",
                "call_outcome": "unsuccessful"
            }
    
    def determine_next_action(self, parsed_outcome: Dict) -> str:
        """
        Determine next action based on parsed outcome.
        Args:
            parsed_outcome: Parsed call outcome
            
        Returns:
            Action string
        """
        if parsed_outcome['payment_status'] == 'paid':
            return "Mark as paid and close"
        
        elif parsed_outcome['payment_promised']:
            promise_date = parsed_outcome.get('payment_promise_date')
            if promise_date:
                return f"Follow up on {promise_date.strftime('%Y-%m-%d')}"
            return "Follow up in 2 days"
        
        elif parsed_outcome['needs_invoice_resend']:
            return "Resend invoice immediately"
        
        elif parsed_outcome['customer_disputed']:
            return "Escalate to accounts team"
        
        elif parsed_outcome['call_outcome'] == 'needs_escalation':
            return "Escalate to manager"
        
        else:
            return "Follow up in 3 days"
    
    def generate_summary(self, parsed_outcome: Dict) -> str:
        """
        Generate human-readable summary from parsed outcome.
        Args:
            parsed_outcome: Parsed call outcome
            
        Returns:
            Summary string
        """
        summary_parts = []
        
        # Payment status
        status = parsed_outcome.get('payment_status', 'unknown')
        if status == 'paid':
            summary_parts.append("Customer confirmed payment already made")
        elif status == 'will_pay':
            summary_parts.append("Customer will make payment")
        elif status == 'disputed':
            summary_parts.append("Customer disputed the invoice")
        
        # Promise date
        if parsed_outcome.get('payment_promised'):
            promise_date = parsed_outcome.get('payment_promise_date')
            if promise_date:
                summary_parts.append(f"Promised to pay by {promise_date.strftime('%d %B %Y')}")
        
        # Invoice resend
        if parsed_outcome.get('needs_invoice_resend'):
            summary_parts.append("Requested invoice to be resent")
        
        # Dispute
        if parsed_outcome.get('customer_disputed'):
            reason = parsed_outcome.get('dispute_reason', 'No reason provided')
            summary_parts.append(f"Dispute reason: {reason}")
        
        # Language
        lang = parsed_outcome.get('language_detected', 'unknown')
        summary_parts.append(f"Language: {lang.title()}")
        
        # Sentiment
        sentiment = parsed_outcome.get('customer_sentiment', 'neutral')
        summary_parts.append(f"Sentiment: {sentiment.title()}")
        
        # Notes
        if parsed_outcome.get('notes'):
            summary_parts.append(parsed_outcome['notes'])
        
        return " | ".join(summary_parts)


# Global instance
response_parser = ResponseParser()