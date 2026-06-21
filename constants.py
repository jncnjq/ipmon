#!/usr/bin/env python3
STATE_UNKNOWN = -1
STATE_DOWN = 0
STATE_UP = 1
CHECK_ICMP = "ICMP"
CHECK_TCP = "TCP"
DEFAULT_TCP_PORT = 3389
def state_to_text(state):
    if state == STATE_UP:
        return "UP"
    if state == STATE_DOWN:
        return "DOWN"
    return "UNKNOWN"
def availability(total, success):
    if total == 0:
        return 0.0
    return round(
        success * 100.0 / total,
        4
    )
def tier(percent):
    if percent >= 99.995:
        return "IV"
    if percent >= 99.982:
        return "III"
    if percent >= 99.741:
        return "II"
    return "I"