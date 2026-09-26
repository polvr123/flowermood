import argparse
import json
import socket
import time
from collections import deque

# Import order matters: setuptools installs a local `distutils` shim (needed by
# tensorflow, a dependency of fer, on Python 3.12+ where distutils was removed
# from the stdlib) as a side effect of being imported. It must run before fer.
import setuptools  # noqa: F401
import cv2
import numpy as np
from fer import FER
import mediapipe as mp

UDP_HOST = "127.0.0.1"
UDP_PORT = 5555
SEND_INTERVAL_S = 0.1  # fixed 10 Hz send rate, independent of capture/inference rate
EMA_ALPHA = 0.2  # smoothing factor for valence/calm; lower = smoother/slower to react
LANDMARK_WINDOW_S = 4.0  # rolling window for calm's landmark-variance calculation
CALM_VARIANCE_SCALE = 0.0005  # empirical scale mapping landmark variance to calm's [0,1] range
CAMERA_INDEX = 1  # fallback if auto-detection below finds nothing
CAMERA_PROBE_COUNT = 4  # how many camera indices to check when auto-detecting
CAMERA_WARMUP_FRAMES = 5  # frames to skip while auto-exposure settles, before judging brightness
CAMERA_BRIGHTNESS_MIN = 5.0  # mean pixel value below this is treated as a dead/black feed (e.g. inactive Continuity Camera)


def find_working_camera():
    """macOS assigns camera indices dynamically (e.g. an iPhone's Continuity
    Camera can occupy index 0 only when nearby/unlocked), so the built-in
    webcam's index shifts around. Probe each index and pick the first one
    that actually produces a non-black frame."""
    for index in range(CAMERA_PROBE_COUNT):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            continue
        brightness = 0.0
        for _ in range(CAMERA_WARMUP_FRAMES):
            ok, frame = cap.read()
            if ok:
                brightness = frame.mean()
        if brightness >= CAMERA_BRIGHTNESS_MIN:
            return cap, index
        cap.release()
    return None, None


class EmotionServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.emotion_detector = FER(mtcnn=False)
        self.landmark_history = deque()  # (timestamp, xy array)
        self.smoothed_valence = 0.0
        self.smoothed_calm = 0.0
        self._has_smoothed_state = False

    def close(self):
        self.face_mesh.close()
        self.sock.close()

    def _ema(self, previous, raw):
        if not self._has_smoothed_state:
            return raw
        return EMA_ALPHA * raw + (1 - EMA_ALPHA) * previous

    def _raw_valence(self, frame_bgr):
        detections = self.emotion_detector.detect_emotions(frame_bgr)
        if not detections:
            return None
        emotions = detections[0]["emotions"]
        return emotions.get("happy", 0.0) - emotions.get("sad", 0.0)

    def _raw_calm(self, landmarks_xy, now):
        self.landmark_history.append((now, landmarks_xy))
        while self.landmark_history and now - self.landmark_history[0][0] > LANDMARK_WINDOW_S:
            self.landmark_history.popleft()
        if len(self.landmark_history) < 2:
            return None
        stacked = np.stack([xy for _, xy in self.landmark_history])
        variance = float(np.mean(np.var(stacked, axis=0)))
        normalized_variance = min(variance / CALM_VARIANCE_SCALE, 1.0)
        return 1.0 - normalized_variance

    def process_frame(self, frame_bgr, now):
        """Returns (face_detected, valence, calm), holding last smoothed values if no face."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        face_detected = bool(results.multi_face_landmarks)

        if not face_detected:
            return face_detected, self.smoothed_valence, self.smoothed_calm

        landmarks = results.multi_face_landmarks[0].landmark
        landmarks_xy = np.array([[lm.x, lm.y] for lm in landmarks], dtype=np.float32)

        raw_valence = self._raw_valence(frame_bgr)
        raw_calm = self._raw_calm(landmarks_xy, now)

        if raw_valence is not None:
            self.smoothed_valence = self._ema(self.smoothed_valence, raw_valence)
        if raw_calm is not None:
            self.smoothed_calm = self._ema(self.smoothed_calm, raw_calm)
        self._has_smoothed_state = True

        return face_detected, self.smoothed_valence, self.smoothed_calm

    def send_state(self, face_detected, valence, calm, now):
        packet = {
            "valence": round(float(np.clip(valence, -1.0, 1.0)), 4),
            "calm": round(float(np.clip(calm, 0.0, 1.0)), 4),
            "face_detected": face_detected,
            "timestamp": now,
        }
        self.sock.sendto(json.dumps(packet).encode("utf-8"), (UDP_HOST, UDP_PORT))
        return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="open a preview window of the webcam feed")
    args = parser.parse_args()

    server = EmotionServer()
    cap, index = find_working_camera()
    if cap is None:
        raise RuntimeError("Could not find a working webcam among the probed camera indices")
    print(f"Using camera index {index}")

    last_send = 0.0
    face_detected = False
    valence = 0.0
    calm = 0.0

    try:
        while True:
            ok, frame = cap.read()
            now = time.monotonic()

            if not ok:
                # Webcam hiccup/disconnect: treat as "no face" and keep retrying
                # rather than crashing; cap.read() will succeed again on reconnect.
                face_detected = False
                time.sleep(0.1)
            else:
                face_detected, valence, calm = server.process_frame(frame, now)
                if args.show:
                    label = f"valence={valence:+.2f} calm={calm:.2f} face={face_detected}"
                    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow("emotion_server preview (q to quit)", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

            if now - last_send >= SEND_INTERVAL_S:
                server.send_state(face_detected, valence, calm, now)
                print(f"valence={valence:+.2f} calm={calm:.2f} face_detected={face_detected}")
                last_send = now
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()
        server.close()


if __name__ == "__main__":
    main()
