import cv2
from typing import Optional, Tuple, Union, List


class VideoInput:
    """Simple webcam/video capture wrapper with Windows backend fallbacks.

    On Windows, some UVC cameras work better with MSMF, others with DSHOW.
    This wrapper tries the requested backend first, then falls back.
    """

    def __init__(self, source: Union[int, str] = 0, width: Optional[int] = 640, height: Optional[int] = 480, api_preference: Optional[str] = "auto"):
        self.source = source
        self.cap = None
        self._open_with_fallbacks(source, api_preference)
        if self.cap and self.cap.isOpened():
            if width is not None:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            if height is not None:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def is_opened(self) -> bool:
        return bool(self.cap) and self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[object]]:
        if not self.cap:
            return False, None
        return self.cap.read()

    def release(self) -> None:
        if self.cap:
            self.cap.release()

    @staticmethod
    def _api_code_from_name(name: Optional[str]) -> List[int]:
        # Map friendly names to OpenCV API preference codes
        if name is None or name.lower() in ("auto", "any"):
            return [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        n = name.lower()
        if n in ("msmf", "mf"):
            return [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        if n in ("dshow", "directshow"):
            return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        # Fallback to ANY if unknown
        return [cv2.CAP_ANY]

    def _open_with_fallbacks(self, source: Union[int, str], api_preference: Optional[str]) -> None:
        api_order = self._api_code_from_name(api_preference)
        for api in api_order:
            cap = cv2.VideoCapture(source, api)
            if cap is not None and cap.isOpened():
                self.cap = cap
                return
            if cap is not None:
                cap.release()
        # final attempt without explicit API (some OpenCV builds ignore the second arg)
        cap = cv2.VideoCapture(source)
        if cap is not None and cap.isOpened():
            self.cap = cap
        else:
            if cap is not None:
                cap.release()

    @staticmethod
    def list_available_cameras(max_index: int = 10, api_preference: Optional[str] = "auto") -> List[int]:
        available = []
        # Suppress verbose backend warnings during probing
        _restore_level = None
        try:
            if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
                _restore_level = getattr(cv2.utils.logging, "LOG_LEVEL_INFO", None)
                try:
                    cv2.utils.logging.setLogLevel(getattr(cv2.utils.logging, "LOG_LEVEL_ERROR", 2))
                except Exception:
                    pass
        except Exception:
            pass
        for idx in range(max_index + 1):
            apis = VideoInput._api_code_from_name(api_preference)
            opened = False
            for api in apis:
                cap = cv2.VideoCapture(idx, api)
                if cap is not None and cap.isOpened():
                    opened = True
                    cap.release()
                    break
                if cap is not None:
                    cap.release()
            if not opened:
                # try default
                cap = cv2.VideoCapture(idx)
                if cap is not None and cap.isOpened():
                    opened = True
                if cap is not None:
                    cap.release()
            if opened:
                available.append(idx)
        # Try restore log level
        try:
            if _restore_level is not None and hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
                cv2.utils.logging.setLogLevel(_restore_level)
        except Exception:
            pass
        return available
