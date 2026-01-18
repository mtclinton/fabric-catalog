"""
Background scheduler for running scrapers daily
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from .scheduled_scraper import scrape_all_bookmarks


def start_scheduler():
    """Start the background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Run daily at 2 AM
    scheduler.add_job(
        run_scraper_job,
        trigger=CronTrigger(hour=2, minute=0),
        id='daily_scrape',
        name='Daily fabric scraping',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started - will run daily at 2 AM")
    return scheduler


def run_scraper_job():
    """Wrapper to run async scraper"""
    asyncio.run(scrape_all_bookmarks())
