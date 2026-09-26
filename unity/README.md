# Unity client
o 
Not yet created. Open Unity Hub, create a new project here using the
**Universal 3D (URP)** template, Unity 2022 LTS or newer, with this `unity/`
folder as the project root.

Once created, build order (see `../docs/mood_garden_spec.pdf` section 7):

1. `UdpReceiver` — background-thread `UdpClient` listening on port 5555,
   writing into a thread-safe latest-value buffer.
2. `EmotionState` — singleton exposing `CurrentValence` / `CurrentCalm`
   (per-frame `Mathf.Lerp`'d, holding last values if no packet for 2s) and
   `IsConnected`.
3. Placeholder flower + trivial visual (e.g. scale) wired to `bloomAmount` to
   confirm the pipeline end to end.
4. Real flower model/material with stem-angle and color blending
   (section 5.2).
5. Tune `growthRate`, EMA alpha, and lerp speeds against the reference
   photos.
