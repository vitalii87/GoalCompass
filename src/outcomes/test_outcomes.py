# src/tools/test_outcomes.py

from src.outcomes.outcome_engine import OutcomeEngine
from src.signals.signals_engine import SignalsEngine


signals_engine = SignalsEngine()
outcome_engine = OutcomeEngine()

signals = signals_engine.generate_for_session(
    process_name="worldoftanks.exe",
    category="time_wasting",
    seconds=7200,
)

for signal in signals:
    print("SIGNAL:")
    print(signal)

    outcome = outcome_engine.generate_from_signal(signal)

    print()
    print("OUTCOME:")
    print(outcome)
    print("-" * 50)
