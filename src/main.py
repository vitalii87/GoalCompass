import time
from datetime import datetime, date

from src.monitor.process_monitor import get_active_process_info
from src.classifier.classifier import classify
from src.coach.coach_engine import evaluate
from src.notifier.notifier import notify
from src.logger.logger import log
from src.config.config import CHECK_INTERVAL_SECONDS


def main():
    current_state = None
    current_process = None
    state_started_at = None
    warning_sent = False

    daily_date = date.today()
    daily_time_by_process = {}

    while True:
        now = datetime.now()
        today = now.date()

        if today != daily_date:
            daily_date = today
            daily_time_by_process = {}
            log("New day started. Daily counters reset.")

        info = get_active_process_info()
        process_name = info["process_name"]
        window_title = info["window_title"]

        state = classify(process_name)
        rule = evaluate(state)

        mode = rule["mode"]
        threshold_seconds = rule["threshold_seconds"]
        notify_on_enter = rule["notify_on_enter"]
        message = rule["message"]

        state_changed = (
            state != current_state or process_name != current_process
        )

        if state_changed:
            current_state = state
            current_process = process_name
            state_started_at = now
            warning_sent = False

            log(f"STATE CHANGED: {process_name} | {window_title} -> {state}")

            if notify_on_enter and message:
                notify(message)

            if mode == "none":
                log("Нейтральна або невідома активність. Без втручання.")

        else:
            duration = (now - state_started_at).total_seconds()

            log(
                f"STATE HOLD: {process_name} | {window_title} -> "
                f"{state} for {int(duration)} sec"
            )

            if mode == "instant" and threshold_seconds > 0 and not warning_sent:
                if duration >= threshold_seconds and message:
                    notify(message)
                    warning_sent = True

        if mode == "daily_accumulate":
            daily_time_by_process.setdefault(process_name, 0)
            daily_time_by_process[process_name] += CHECK_INTERVAL_SECONDS

            daily_total = daily_time_by_process[process_name]

            log(
                f"DAILY ACCUMULATE: {process_name} -> {int(daily_total)} sec today"
            )

            if daily_total >= threshold_seconds and not warning_sent and message:
                notify(message)
                warning_sent = True

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()