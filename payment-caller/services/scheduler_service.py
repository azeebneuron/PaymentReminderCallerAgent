"""
Scheduler service for automated daily calls.
"""
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from services.call_orchestrator import call_orchestrator
from config.settings import settings
from utils.logger import logger


# Global scheduler instance
scheduler = BackgroundScheduler()


def run_daily_calls():
    """
    Job function to run daily calls.
    This wraps the async function for the scheduler.
    """
    try:
        logger.info("Starting scheduled daily calls...")
        asyncio.run(call_orchestrator.process_pending_payments())
    except Exception as e:
        logger.error(f"Error in scheduled daily calls: {e}")


def start_scheduler():
    """Start the scheduler with configured jobs."""
    try:
        # Parse time from settings
        hour, minute = map(int, settings.daily_run_time.split(":"))
        
        # Create timezone
        tz = pytz.timezone(settings.timezone)
        
        # Add daily job
        scheduler.add_job(
            run_daily_calls,
            trigger=CronTrigger(
                hour=hour,
                minute=minute,
                timezone=tz
            ),
            id='daily_payment_calls',
            name='Daily Payment Reminder Calls',
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        
        logger.info(f"Scheduler started. Daily calls scheduled at {settings.daily_run_time} {settings.timezone}")
        logger.info(f"Next run: {scheduler.get_job('daily_payment_calls').next_run_time}")
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    try:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")


def trigger_immediate_run():
    """Trigger an immediate run of the daily calls job."""
    try:
        logger.info("Triggering immediate run of daily calls...")
        run_daily_calls()
    except Exception as e:
        logger.error(f"Error in immediate run: {e}")