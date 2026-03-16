"""
Runs the pipeline twice a day (9am and 9pm local time).
Keep this process running in the background (e.g. via tmux or a system service).
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline import run


scheduler = BlockingScheduler()

# Runs at 9:00 AM and 9:00 PM every day
scheduler.add_job(run, "cron", hour="9,21", minute=0)

print("[scheduler] Starting — will check for new VODs at 9am and 9pm daily.")
print("[scheduler] Running once now on startup...")
run()

scheduler.start()
