import urllib.parse
import urllib.request
from typing import Optional

# Mapping: group 1-5 -> bravo/charlie/delta/echo/foxtrot (example names; user provided 'bravo' for sample)
# If you prefer numeric group directly, we will pass as number.

group_number_to_param = {
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
}

# Mapping: hand gesture -> message code (1..6) or string as needed
# The user asked: "message" corresponds to 6 hand actions. We'll map:
# 1=FIST, 2=FIVE, 3=GOOD, 4=ROCK, 5=GUN, 6=F_CK

gesture_to_message = {
    "FIST": "1",
    "FIVE": "2",
    "GOOD": "3",
    "ROCK": "4",
    "GUN": "5",
    "F_CK": "6",
}


def build_control_url(base: str, group_number: int, gesture: str, id_value: Optional[str] = "") -> str:
    """Build control URL like: http://localhost:8080/control?group=bravo&id=&message=2

    - group: 1-5 (as per requirement) – sent as numeric string
    - id: empty string
    - message: 6 options mapped from gesture
    """
    group_param = group_number_to_param.get(int(group_number), str(group_number))
    message_param = gesture_to_message[gesture]
    query = {
        "group": group_param,
        "id": id_value or "",
        "message": message_param,
    }
    return f"{base.rstrip('/')}/control?{urllib.parse.urlencode(query)}"


def send_control(base: str, group_number: int, gesture: str, timeout: float = 2.0) -> bool:
    """Send GET request. Returns True on HTTP 200."""
    url = build_control_url(base, group_number, gesture)
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return 200 <= resp.status < 300
