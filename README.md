# Hand Gesture Synth
Play Music without touching any instrument!! Just make some hand signs and this program does the rest.
Each handsign plays a note or a chord!
<img width="795" height="632" alt="ss1" src="https://github.com/user-attachments/assets/a16a900c-1814-495e-91fb-b01aedab2eef" />


## How to Use:
There are three different modes:
- Notes
- Chords
- InKey

Going over them one by one:

### Notes Mode:
Your right hands plays the 7 base notes while the left hand controls which octave will those notes be played in, so it is basically a piano wihtout the sharp and flat keys!
<img width="800" height="637" alt="Screenshot 2026-10-19 222213" src="https://github.com/user-attachments/assets/c7cd6cdc-85a1-402f-98dd-323211c0c6f8" />


### Chords Mode: 
Your right hand determines the key and your left hand determines the scale of the chord to be played, Very fun to use to sing along the song of your liking, all chords are easy to play just need a teensy tiny bit of memorizing.
Use W/S to increase/decrease the octave.
<img width="857" height="680" alt="Screenshot 2026-10-19 222316" src="https://github.com/user-attachments/assets/972093e2-ccbd-4094-9e24-3b354e221987" />


### InKey Mode:
Your left hand determines the octave a note should be played in, while your right hand determines the note that should be played, but the difference from the first mode is that you can select a key to play in using j/k to cycle through them.
Any handsign you produce a note that sounds coherent, nothing sounds off, so its good for beginners in music to play around with coz it almost always sounds pleasant.

## Handsigns:
All signs for entries left to right wil go like: 

| Sign | Right hand (root) | Left hand (chord type) |
|---|---|---|
| Index | C | Major |
| Index + middle | D | Minor |
| Three fingers | E | 7 |
| Four fingers | F | 5 |
| Open hand | G | dim |
| Thumb only | A | dim7 |
| Thumb + index | B | aug |
| Thumb + index + middle | C# | sus2 |
| Thumb + three fingers | D# | sus4 |
| Pinky only | F# | maj7 |
| Thumb + pinky | G# | m7 |
| Index + pinky | A# | 7sus4 |

## Controls

| Key | Action |
|---|---|
| M or 1 / 2 / 3 | Switch mode |
| J / K | Previous / next key (Key mode) |
| T | Major / minor (Key mode) |
| W / S | Octave up / down (Chords mode) |
| Esc | Quit |

## Setup (Windows)

1. Install Python 3.12 and tick "Add python.exe to PATH".
2. In a terminal inside the project folder:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Sound comes from the Microsoft GS Wavetable Synth built into Windows.

## Credits

Built with OpenCV, MediaPipe, and mido and lots of love lol.
Made by Mohd Altaaf
