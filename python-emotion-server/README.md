# Python emotion server

Reads webcam expression, computes `valence` and `calm`, streams them as UDP JSON
packets to `127.0.0.1:5555` at a fixed 10 Hz. See `../docs/mood_garden_spec.pdf`
section 4 for the full spec.

## Setup

```
cd python-emotion-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```
python emotion_server.py
```

Prints `valence`, `calm`, and `face_detected` to the console at 10 Hz. Smiling
should move valence toward +1.0; frowning toward -1.0. Holding still for 10+
seconds should move calm toward 1.0. Covering the webcam should flip
`face_detected` to `false` within about a second without crashing the process.
