from typing import Optional
import socket


class Controller:
    """Control output in manual or automatic mode."""

    def __init__(self, mode: str = "auto") -> None:
        assert mode in {"manual", "auto"}
        self.mode = mode
        self._last_action: Optional[str] = None
        # UDP client (lazy)
        self._udp_sock: Optional[socket.socket] = None
        self._udp_addr: Optional[tuple] = None

    def set_mode(self, mode: str) -> None:
        assert mode in {"manual", "auto"}
        self.mode = mode

    def manual_execute(self, command: str) -> Optional[str]:
        """Manually output a gaze action string."""
        return command

    def auto_step(self, gaze_action: Optional[str]) -> Optional[str]:
        """Return action when not CENTER; otherwise None."""
        if gaze_action and gaze_action != "CENTER":
            if gaze_action != self._last_action:
                self._last_action = gaze_action
                return gaze_action
            return None
        self._last_action = gaze_action
        return None

    # --- UDP ---
    def setup_udp(self, ip: str, port: int) -> None:
        self._udp_addr = (ip, int(port))
        if self._udp_sock is None:
            self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_udp(self, message: str) -> bool:
        if not self._udp_addr:
            return False
        if self._udp_sock is None:
            self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._udp_sock.sendto(message.encode("utf-8"), self._udp_addr)
            return True
        except Exception:
            return False

    def map_action_to_code(self, action: Optional[str]) -> int:
        if not action:
            return 0
        mapping = {
            "LEFT": 1,
            "RIGHT": 2,
            "UP": 3,
            "DOWN": 4,
            "LEFT_EYE_CLOSED": 5,
            "RIGHT_EYE_CLOSED": 6,
        }
        return mapping.get(action, 0)
