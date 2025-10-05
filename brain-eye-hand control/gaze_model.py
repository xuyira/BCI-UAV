from collections import Counter, deque
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np


GAZE_ACTIONS = [
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "CENTER",
    "LEFT_EYE_CLOSED",
    "RIGHT_EYE_CLOSED",
]


class GazeModel:
    """Lightweight CPU gaze direction (UP/DOWN/LEFT/RIGHT/CENTER) with smoothing.

    Pipeline:
      - Detect face and eyes via Haar cascades
      - For each eye ROI: threshold to find dark pupil region, get centroid
      - Normalize centroid position within eye box to [-1, 1] in x/y
      - Average both eyes' normalized offsets; map to direction via thresholds
      - Temporal smoothing via majority vote over recent actions

    Note:
      - Phase 1: directions only (no per-eye blink). 'CLOSED' reserved for phase 2.
    """

    def __init__(self, history_size: int = 5, x_thresh: float = 0.15, y_thresh: float = 0.18) -> None:
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        # Try two eye cascades; some cameras work better with the simpler one
        self.eye_cascade_primary = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml")
        self.eye_cascade_alt = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        # Detection parameters
        self.face_scale_factor = 1.1
        self.face_min_neighbors = 3
        self.face_min_size = 60
        self.eye_scale_factor = 1.05
        self.eye_min_neighbors = 2
        self.eye_min_size = 15
        self.history: Deque[str] = deque(maxlen=history_size)
        self.x_thresh = x_thresh
        self.y_thresh = y_thresh
        # asymmetric vertical thresholds and gains (to make DOWN easier to trigger)
        self.y_thresh_up: float = max(0.12, y_thresh)
        self.y_thresh_down: float = max(0.10, y_thresh * 0.8)
        self.v_gain_up: float = 1.0
        self.v_gain_down: float = 1.3
        # adaptive neutral baseline (EMA) to reduce vertical bias
        self.baseline_nx: float = 0.0
        self.baseline_ny: float = 0.0
        self._baseline_alpha: float = 0.05
        self._last_debug: Dict = {}
        # eye size adaptive gain reference
        self.eye_ref: float = 60.0
        # per-eye blink counters
        self._no_pupil_left: int = 0
        self._no_pupil_right: int = 0
        self._blink_frames_threshold: int = 3

    def _detect_face(self, gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=self.face_scale_factor, 
            minNeighbors=self.face_min_neighbors, 
            minSize=(self.face_min_size, self.face_min_size)
        )
        if len(faces) == 0:
            return None
        # choose the largest face
        x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
        return int(x), int(y), int(w), int(h)

    def _detect_eyes(self, face_gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        # Use upper 70% of face to avoid mouth/nose false positives
        fh, fw = face_gray.shape[:2]
        face_eye_roi = face_gray[0:int(fh * 0.7), :]
        eyes = self.eye_cascade_primary.detectMultiScale(
            face_eye_roi, 
            scaleFactor=self.eye_scale_factor, 
            minNeighbors=self.eye_min_neighbors, 
            minSize=(self.eye_min_size, self.eye_min_size)
        )
        if len(eyes) == 0:
            eyes = self.eye_cascade_alt.detectMultiScale(
                face_eye_roi, 
                scaleFactor=self.eye_scale_factor, 
                minNeighbors=self.eye_min_neighbors, 
                minSize=(self.eye_min_size, self.eye_min_size)
            )
        # Keep up to two largest detections
        eyes = sorted(eyes, key=lambda b: b[2] * b[3], reverse=True)[:2]
        # Map back to full face coordinates
        mapped = []
        for (x, y, w, h) in eyes:
            mapped.append((int(x), int(y), int(w), int(h)))
        return mapped

    def _pupil_centroid(self, eye_gray: np.ndarray) -> Optional[Tuple[float, float]]:
        # Focus on central ROI to avoid borders; cut more top/bottom to reduce eyelid interference
        h, w = eye_gray.shape[:2]
        x0 = int(w * 0.25)
        y0 = int(h * 0.25)
        x1 = int(w * 0.75)
        y1 = int(h * 0.75)
        roi = eye_gray[y0:y1, x0:x1]
        if roi.size == 0:
            return None
        # Preprocess
        eq = cv2.equalizeHist(roi)
        blur = cv2.GaussianBlur(eq, (7, 7), 0)
        # Invert-binary with Otsu; pupils are darker
        _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # Morph close small gaps
        kernel = np.ones((3, 3), np.uint8)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)
        # Find largest contour
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        if area < max(20, 0.003 * roi.shape[0] * roi.shape[1]):  # allow smaller pupils to reduce false missing
            return None
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return None
        cx = M["m10"] / M["m00"] + x0
        cy = M["m01"] / M["m00"] + y0
        return float(cx), float(cy)

    def _normalize(self, cx: float, cy: float, w: int, h: int) -> Tuple[float, float]:
        # Normalize to [-1, 1], origin at center
        nx = (cx / max(w, 1) - 0.5) * 2.0
        ny = (cy / max(h, 1) - 0.5) * 2.0
        return nx, ny

    def _classify_direction(self, nx: float, ny: float) -> str:
        # y axis: smaller cy (upper) -> ny negative -> UP
        # apply asymmetric vertical gain
        ny_eff = ny * (self.v_gain_down if ny > 0 else self.v_gain_up)
        if abs(nx) < self.x_thresh and (
            (ny_eff < 0 and abs(ny_eff) < self.y_thresh_up) or (ny_eff >= 0 and abs(ny_eff) < self.y_thresh_down)
        ):
            return "CENTER"
        if abs(ny_eff) >= abs(nx):
            return "UP" if ny_eff < 0 else "DOWN"
        else:
            return "LEFT" if nx < 0 else "RIGHT"

    def _smooth(self, action: str) -> str:
        self.history.append(action)
        counts = Counter(self.history)
        return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]

    def predict(self, frame) -> Dict[str, Optional[Tuple[int, int]]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face = self._detect_face(gray)
        if face is None:
            action = self._smooth("CENTER")
            self._last_debug = {"reason": "no_face"}
            return {"action": action, "pupil": None}

        fx, fy, fw, fh = face
        face_gray = gray[fy : fy + fh, fx : fx + fw]
        eyes = self._detect_eyes(face_gray)
        if len(eyes) == 0:
            action = self._smooth("CENTER")
            self._last_debug = {"reason": "no_eyes", "face": (fx, fy, fw, fh)}
            return {"action": action, "pupil": None}

        centers_norm: List[Tuple[float, float]] = []
        pupils_global: List[Tuple[int, int]] = []
        per_eye_centroid: List[Optional[Tuple[float, float]]] = []
        for (ex, ey, ew, eh) in eyes:
            roi = face_gray[ey : ey + eh, ex : ex + ew]
            centroid = self._pupil_centroid(roi)
            if centroid is None:
                per_eye_centroid.append(None)
                continue
            cx, cy = centroid
            nx, ny = self._normalize(cx, cy, ew, eh)
            centers_norm.append((nx, ny))
            per_eye_centroid.append((cx, cy))
            # map to full-frame coordinates for visualization
            pupils_global.append((fx + ex + int(cx), fy + ey + int(cy)))

        # Determine left/right eye order by x within face coords (mirrored frame already)
        left_eye_idx = None
        right_eye_idx = None
        if len(eyes) == 1:
            left_eye_idx = 0 if eyes[0][0] < fw / 2 else None
            right_eye_idx = 0 if left_eye_idx is None else None
        else:
            # indices sorted by x
            sorted_by_x = sorted(list(enumerate(eyes)), key=lambda kv: kv[1][0])
            left_eye_idx = sorted_by_x[0][0]
            right_eye_idx = sorted_by_x[1][0]

        # per-eye pupil presence
        had_left = left_eye_idx is not None and left_eye_idx < len(per_eye_centroid) and per_eye_centroid[left_eye_idx] is not None
        had_right = right_eye_idx is not None and right_eye_idx < len(per_eye_centroid) and per_eye_centroid[right_eye_idx] is not None

        # update blink counters
        self._no_pupil_left = 0 if had_left else min(self._blink_frames_threshold + 10, self._no_pupil_left + 1)
        self._no_pupil_right = 0 if had_right else min(self._blink_frames_threshold + 10, self._no_pupil_right + 1)

        left_closed = self._no_pupil_left >= self._blink_frames_threshold
        right_closed = self._no_pupil_right >= self._blink_frames_threshold

        # Blink debounce: emit only when counter == threshold, not on every frame
        blink_action: Optional[str] = None
        if left_closed and not right_closed and self._no_pupil_left == self._blink_frames_threshold:
            blink_action = "LEFT_EYE_CLOSED"
        elif right_closed and not left_closed and self._no_pupil_right == self._blink_frames_threshold:
            blink_action = "RIGHT_EYE_CLOSED"

        if blink_action is not None:
            self._last_debug = {
                "face": (fx, fy, fw, fh),
                "eyes": eyes,
                "pupils": pupils_global,
                "blink": blink_action,
                "no_pupil_left": self._no_pupil_left,
                "no_pupil_right": self._no_pupil_right,
            }
            return {"action": blink_action, "pupil": None}

        # If pupils reappear, keep debug counts visible
        if had_left and had_right:
            pass

        if not centers_norm:
            action = self._smooth("CENTER")
            self._last_debug = {"reason": "no_pupil", "face": (fx, fy, fw, fh), "eyes": eyes}
            return {"action": action, "pupil": None}

        nx_avg = float(np.mean([c[0] for c in centers_norm]))
        ny_avg = float(np.mean([c[1] for c in centers_norm]))
        # Adaptive gain based on eye size (larger eyes => smaller gain)
        mean_ew = float(np.mean([e[2] for e in eyes])) if eyes else 40.0
        eye_ref = self.eye_ref
        gain = min(3.0, max(0.8, eye_ref / max(mean_ew, 1.0)))
        nx_avg *= gain
        ny_avg *= gain
        # subtract adaptive neutral baseline
        nx_adj = nx_avg - self.baseline_nx
        ny_adj = ny_avg - self.baseline_ny
        raw_action = self._classify_direction(nx_adj, ny_adj)
        action = self._smooth(raw_action)
        # Update baseline slowly when near center to avoid drift
        if action == "CENTER" and abs(nx_adj) < self.x_thresh and abs(ny_adj) < self.y_thresh:
            self.baseline_nx = (1 - self._baseline_alpha) * self.baseline_nx + self._baseline_alpha * nx_avg
            self.baseline_ny = (1 - self._baseline_alpha) * self.baseline_ny + self._baseline_alpha * ny_avg

        # Choose one pupil to display (average if two)
        if pupils_global:
            px = int(np.mean([p[0] for p in pupils_global]))
            py = int(np.mean([p[1] for p in pupils_global]))
            pupil_pt: Optional[Tuple[int, int]] = (px, py)
        else:
            pupil_pt = None

        # Save debug info
        self._last_debug = {
            "face": (fx, fy, fw, fh),
            "eyes": eyes,
            "pupils": pupils_global,
            "nx_avg": nx_avg,
            "ny_avg": ny_avg,
            "nx_adj": nx_adj,
            "ny_adj": ny_adj,
            "raw_action": raw_action,
            "smoothed": action,
            "blink": None,
            "no_pupil_left": self._no_pupil_left,
            "no_pupil_right": self._no_pupil_right,
        }
        return {"action": action, "pupil": pupil_pt}

    def get_debug(self) -> Dict:
        return self._last_debug

    # --- Calibration/online tuning API ---
    def reset_baseline(self) -> None:
        self.baseline_nx = 0.0
        self.baseline_ny = 0.0

    def set_thresholds(self, x_thresh: float, y_up: float, y_down: float) -> None:
        self.x_thresh = float(x_thresh)
        self.y_thresh_up = float(y_up)
        self.y_thresh_down = float(y_down)

    def set_vertical_gains(self, gain_up: float, gain_down: float) -> None:
        self.v_gain_up = float(gain_up)
        self.v_gain_down = float(gain_down)

    def set_eye_ref(self, eye_ref: float) -> None:
        self.eye_ref = float(eye_ref)

    def set_blink_threshold(self, frames: int) -> None:
        self._blink_frames_threshold = int(frames)

    def set_detection_params(self, face_scale: float = None, face_neighbors: int = None, 
                           face_minsize: int = None, eye_scale: float = None, eye_neighbors: int = None, 
                           eye_minsize: int = None) -> None:
        """Set detection parameters for better adaptation to different cameras/lighting."""
        if face_scale is not None:
            self.face_scale_factor = float(face_scale)
        if face_neighbors is not None:
            self.face_min_neighbors = int(face_neighbors)
        if face_minsize is not None:
            self.face_min_size = int(face_minsize)
        if eye_scale is not None:
            self.eye_scale_factor = float(eye_scale)
        if eye_neighbors is not None:
            self.eye_min_neighbors = int(eye_neighbors)
        if eye_minsize is not None:
            self.eye_min_size = int(eye_minsize)
