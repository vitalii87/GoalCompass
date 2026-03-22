

def evaluate(state):
    if state == "productive":
        return "good"
    elif state == "distracting":
        return "warning"
    else:
        return "neutral"