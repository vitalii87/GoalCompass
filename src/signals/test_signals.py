# src/tools/test_signals.py

from src.signals.signals_engine import SignalsEngine


engine = SignalsEngine()

signals = engine.generate_for_session(
    process_name="worldoftanks.exe",
    category="time_wasting",
    seconds=7200,
)

for signal in signals:
    print(signal)