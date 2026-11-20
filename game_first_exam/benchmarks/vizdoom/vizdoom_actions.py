"""Encode trusted ViZDoom button names and optional native continuous controls."""
import math
import re
from decimal import Decimal

DELTA_BUTTONS = ("LOOK_UP_DOWN_DELTA", "TURN_LEFT_RIGHT_DELTA", "MOVE_LEFT_RIGHT_DELTA")
DECIMAL = r"-?(?:0|[1-9][0-9]{0,63})(?:\.[0-9]{1,64})?"
DURATION = r"(?:@[1-9][0-9]*)?"


def dense_pattern(buttons):
    """Canonical order, with every binary combination supported without enumerating masks."""
    alternatives = [re.escape(b) + "".join(rf"(?:\+{re.escape(other)})?" for other in buttons[i+1:])
                    for i, b in enumerate(buttons)]
    alternative = "|".join(["noop", *alternatives])
    return rf"(?:{alternative})(?:~{DECIMAL},{DECIMAL},{DECIMAL})?{DURATION}"


def encode_action(action, tics, deltas=None):
    if type(tics) is not int or tics < 1:
        raise ValueError("tics must be a positive integer")
    if not isinstance(action, str) or not action or "@" in action or "~" in action:
        raise ValueError("action must be a native ViZDoom button combination")
    if deltas is not None:
        if not isinstance(deltas, dict) or deltas.keys() - set(DELTA_BUTTONS):
            raise ValueError("deltas must map native continuous button names to numbers")
        values = []
        for button in DELTA_BUTTONS:
            value = deltas.get(button, 0)
            if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
                raise ValueError("delta values must be finite numbers")
            text = format(Decimal(str(value)), "f")
            if not re.fullmatch(DECIMAL, text):
                raise ValueError("delta value is outside the representable decimal range")
            values.append(text)
        action = f"{action}~{','.join(values)}"
    return f"{action}@{tics}"
