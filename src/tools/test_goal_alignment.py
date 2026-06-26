# src/tools/test_goal_alignment.py

from src.goals.goal_alignment import GoalAlignmentEngine
from src.goals.goal_loader import load_goals
from src.outcomes.outcome_engine import OutcomeEngine
from src.signals.signals_engine import SignalsEngine


signals_engine = SignalsEngine()
outcome_engine = OutcomeEngine()
alignment_engine = GoalAlignmentEngine()

goals = load_goals()

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

    if outcome:
        print()
        print("GOAL ALIGNMENTS:")

        for goal in goals:
            result = alignment_engine.evaluate(
                goal,
                outcome,
            )

            print(result)

    print("-" * 50)