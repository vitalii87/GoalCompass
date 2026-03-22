import time

from src.monitor.process_monitor import get_active_process_info
from src.classifier.classifier import classify
from src.coach.coach_engine import evaluate
from src.notifier.notifier import notify
from src.logger.logger import log


def main():
    while True:
        info = get_active_process_info()

        process_name = info["process_name"]
        window_title = info["window_title"]

        state = classify(process_name)
        decision = evaluate(state)

        log(f"{process_name} | {window_title} -> {state}")

        if decision == "warning":
            notify("Ти відволікся. Повернись до роботи.")
        elif decision == "good":
            notify("Добре, продовжуй.")

        time.sleep(5)


if __name__ == "__main__":
    main()