# flowermood

flower mood, a webcam-driven plant growth toy.  Python process reads facial
expression and streams `valence`/`calm` signals over UDP to a Unity scene that
grows, blooms, and wilts a single flower 

using unity, meshy

## Layout

- `python-emotion-server/` — webcam/OpenCV/mediapipe emotion signal server
- `unity/` — Unity client (URP) that renders and drives the flower
- `docs/` — spec and design notes

## Progress so far

![Reference flower](docs/reference-flower-bloomed.jpg)

This is the actual real-life flower (celosia + petunias) we're using as the visual
reference, when you smile it blooms when you frown it wilts. 

**Working:**
- Python emotion server reads the webcam, computes `valence` (smile/frown) and
  `calm` (stillness), and streams them over UDP at 10Hz
- Generated a 3D model of the flower/pot from the reference photo (via Meshy,
  image-to-3D), textured with the real colors, imported into Unity 
- `FlowerController` gets `bloomAmount` from sustained valence and then uses
  - a scale multiplier (bigger when blooming, smaller when wilting)
  - a color tint lerp (true colors when blooming, browner when wilting)

**limitation for now:** the generated model is one single pot + plant
all as one piece, so it doesn't wilt naturally, the entire thing just rotates

**Next up:** split the model into separate objects (pot vs. plant, maybe
per-stem) so wilting can actually droop the plant without moving the pot
