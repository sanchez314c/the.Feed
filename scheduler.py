#!/usr/bin/env python3
"""
AIFEED Background Scheduler
This script runs as a background service to automatically refresh data at configured intervals.
"""

import sys
import signal
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from data_manager import DataManager
from utils import logger, load_environment, load_config

class AIFeedScheduler:
    def __init__(self):
        """Initialize the scheduler with configuration."""
        load_environment()
        self.config = load_config()
        self.scheduler = BlockingScheduler(timezone="UTC")
        self.data_manager = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}. Shutting down scheduler...")
        self.stop()
        sys.exit(0)
    
    def _job_listener(self, event):
        """Listen to job events and log them."""
        if event.exception:
            logger.error(f"Scheduled job failed: {event.exception}", exc_info=True)
        else:
            logger.info(f"Scheduled job executed successfully: {event.job_id}")
    
    def scheduled_refresh_job(self):
        """The main job that refreshes data from all sources."""
        logger.info("Scheduler: Starting scheduled data refresh job.")
        try:
            # Initialize data manager if not already done
            if self.data_manager is None:
                self.data_manager = DataManager()
            
            # Perform the refresh
            result = self.data_manager.refresh_data()
            
            if result.get('status') == 'success':
                logger.info("Scheduler: Data refresh job completed successfully.")
            else:
                logger.warning(f"Scheduler: Data refresh job completed with issues: {result}")
                
        except Exception as e:
            logger.error(f"Scheduler: Error during scheduled data refresh: {e}", exc_info=True)
            raise  # Re-raise to trigger the job error event
    
    def start(self):
        """Start the scheduler with configured jobs."""
        # Get refresh interval from config
        scheduler_config = self.config.get('scheduler', {})
        refresh_interval_hours = scheduler_config.get('refresh_interval_hours', 1)
        
        # Add the main refresh job
        self.scheduler.add_job(
            self.scheduled_refresh_job,
            trigger=IntervalTrigger(hours=refresh_interval_hours),
            id="aifeed_refresh_job",
            name="AIFEED Data Refresh",
            max_instances=1,  # Prevent overlapping jobs
            coalesce=True,    # Combine missed jobs into one
            misfire_grace_time=300  # 5 minutes grace time for missed jobs
        )
        
        # Add job event listener
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        logger.info(f"AIFEED Scheduler starting. Data refresh scheduled every {refresh_interval_hours} hour(s).")
        logger.info("Press Ctrl+C to stop the scheduler.")
        
        try:
            # Run an initial refresh immediately
            logger.info("Running initial data refresh...")
            self.scheduled_refresh_job()
            
            # Start the scheduler
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user.")
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped.")

def main():
    """Main entry point for the scheduler."""
    scheduler = AIFeedScheduler()
    scheduler.start()

if __name__ == '__main__':
    main()