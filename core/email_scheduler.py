"""
Automatic Birthday and Anniversary Email Service
This runs in the background and checks every hour for birthdays/anniversaries
based on employee location timezone.

Add this to your Django app to run automatically.
"""

import threading
import time
import logging
from django.core.management import call_command
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailSchedulerService:
    """Background service that runs the email command every hour"""

    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        """Start the background service"""
        if self.running:
            logger.warning("Email scheduler service is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("✅ Email scheduler service started - checking every hour")

    def stop(self):
        """Stop the background service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Email scheduler service stopped")

    def _run_scheduler(self):
        """Main loop that runs every hour"""
        while self.running:
            try:
                current_time = datetime.now()
                logger.info(
                    f"🔍 Checking for birthdays/anniversaries at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Run the management command
                # Run the management command
                call_command("send_birthday_anniversary_emails", hour=9)

                logger.info("✅ Email check completed")

            except Exception as e:
                logger.error(f"❌ Error in email scheduler: {str(e)}")

            # Wait for 1 hour (3600 seconds)
            # Check every minute if we should stop
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(60)  # Sleep for 1 minute, check 60 times = 1 hour


# Global instance
email_scheduler = EmailSchedulerService()
