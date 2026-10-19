import cv2
import mediapipe as mp
import math
import mido

# ---------- MIDI setup ----------
out = mido.open_output(mido.get_output_names()[0])
# 19 church organ, 16 drawbar organ, 48 strings, 73 flute, 89 warm pad, 81 synth lead
out.send(mido.Message('program_change', program=89))
VELOCITY = 80

# ---------- Camera and hand tracking ----------
hands = mp.solutions.hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5,
)
draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

TIPS = [8, 12, 16, 20]
PIPS = [6, 10, 14, 18]


def finger_states(lm):
    p = lm.landmark

    def dist(a, b):
        return math.hypot(p[a].x - p[b].x, p[a].y - p[b].y)

    thumb = dist(4, 17) > dist(3, 17)
    others = [p[t].y < p[k].y for t, k in zip(TIPS, PIPS)]
    return tuple([thumb] + others)     # (thumb, index, middle, ring, pinky)


# ---------- Signs ----------
FIST = (0, 0, 0, 0, 0)

# 12 hand patterns, in order
PATTERNS = [
    (0, 1, 0, 0, 0),   # 1  index
    (0, 1, 1, 0, 0),   # 2  index+middle
    (0, 1, 1, 1, 0),   # 3  three fingers
    (0, 1, 1, 1, 1),   # 4  four fingers
    (1, 1, 1, 1, 1),   # 5  open hand
    (1, 0, 0, 0, 0),   # 6  thumb only
    (1, 1, 0, 0, 0),   # 7  thumb+index
    (1, 1, 1, 0, 0),   # 8  thumb+index+middle
    (1, 1, 1, 1, 0),   # 9  thumb+three fingers
    (0, 0, 0, 0, 1),   # 10 pinky only
    (1, 0, 0, 0, 1),   # 11 thumb+pinky
    (0, 1, 0, 0, 1),   # 12 index+pinky
]

# (name, semitones above C)
ROOTS = [("C", 0), ("D", 2), ("E", 4), ("F", 5), ("G", 7), ("A", 9), ("B", 11),
         ("C#", 1), ("D#", 3), ("F#", 6), ("G#", 8), ("A#", 10)]

# (name, intervals in semitones from the root)
QUALITIES = [
    ("Major", [0, 4, 7]),
    ("Minor", [0, 3, 7]),
    ("7",     [0, 4, 7, 10]),
    ("5",     [0, 7, 12]),
    ("dim",   [0, 3, 6]),
    ("dim7",  [0, 3, 6, 9]),
    ("aug",   [0, 4, 8]),
    ("sus2",  [0, 2, 7]),
    ("sus4",  [0, 5, 7]),
    ("maj7",  [0, 4, 7, 11]),
    ("m7",    [0, 3, 7, 10]),
    ("7sus4", [0, 5, 7, 10]),
]

NOTE_SIGNS = dict(zip(PATTERNS[:7], ROOTS[:7]))   # note mode: just C..B
ROOT_SIGNS = dict(zip(PATTERNS, ROOTS))           # chord mode right hand
QUALITY_SIGNS = dict(zip(PATTERNS, QUALITIES))    # chord mode left hand

# ---------- Interface ----------
CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
QUALITY_NAMES = [q[0] for q in QUALITIES]
AMBER = (0, 184, 255)    # BGR
GREY = (80, 80, 80)


def draw_bar(frame, names, active, y, bar_h=28):
    cell = frame.shape[1] // len(names)
    for i, name in enumerate(names):
        x0 = i * cell
        on = (name == active)
        cv2.rectangle(frame, (x0, y), (x0 + cell - 2, y + bar_h),
                      AMBER if on else GREY, -1)
        cv2.putText(frame, name, (x0 + 4, y + bar_h - 9),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (0, 0, 0) if on else (255, 255, 255), 1)


def hand_text(label, states):
    if label == "Right":
        if states == FIST:
            return "rest"
        table = NOTE_SIGNS if mode == "notes" else ROOT_SIGNS
        return table.get(states, ("?",))[0]
    if mode == "notes":
        return f"Octave {sum(states)}"
    if states == FIST:
        return "Major"
    return QUALITY_SIGNS.get(states, ("?",))[0]


# ---------- State ----------
mode = "notes"                       # "notes" or "chords"
OCTAVE_BASES = {1: 48, 2: 60, 3: 72, 4: 84}
note_base = 60                       # note mode octave (left hand)
chord_base = 48                      # chord mode octave (W / S keys)

sounding = ()                        # MIDI notes currently on
candidate = ()
stable_count = 0
STABLE_FRAMES = 2

# ---------- Main loop ----------
while True:
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    h, w, _ = frame.shape

    right = None    # finger pattern of right hand, None if not seen
    left = None

    if result.multi_hand_landmarks:
        for lm, handed in zip(result.multi_hand_landmarks, result.multi_handedness):
            label = handed.classification[0].label
            states = finger_states(lm)
            if label == "Right":
                right = states
            else:
                left = states

            draw.draw_landmarks(frame, lm, mp.solutions.hands.HAND_CONNECTIONS)
            x = int(lm.landmark[0].x * w)
            y = int(lm.landmark[0].y * h)
            cv2.putText(frame, f"{label}: {hand_text(label, states)}",
                        (x - 40, y + 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # --- decide which notes we WANT right now ---
    # desired = tuple of MIDI notes, () for silence, None to hold (unknown sign)
    desired = None
    active_root = None
    active_quality = None

    if mode == "notes":
        if left is not None and sum(left) in OCTAVE_BASES:
            note_base = OCTAVE_BASES[sum(left)]
        if right is None or right == FIST:
            desired = ()
        elif right in NOTE_SIGNS:
            desired = (note_base + NOTE_SIGNS[right][1],)
    else:
        if right is None or right == FIST:
            desired = ()
        elif right in ROOT_SIGNS:
            if left is None or left == FIST:
                quality = QUALITIES[0]                 # default Major
            else:
                quality = QUALITY_SIGNS.get(left)      # None if unknown sign
            if quality is not None:
                root_name, root_offset = ROOT_SIGNS[right]
                root_midi = chord_base + root_offset
                desired = tuple(root_midi + i for i in quality[1])
                active_root, active_quality = root_name, quality[0]

    # --- stability filter ---
    if desired is not None:
        if desired == candidate:
            stable_count += 1
        else:
            candidate = desired
            stable_count = 1

        # --- note on/off ---
        if stable_count >= STABLE_FRAMES and candidate != sounding:
            for n in candidate:
                if n not in sounding:
                    out.send(mido.Message('note_on', note=n, velocity=VELOCITY))
            for n in sounding:
                if n not in candidate:
                    out.send(mido.Message('note_off', note=n))
            sounding = candidate

    # --- interface ---
    if mode == "chords":
        draw_bar(frame, CHROMATIC, active_root, 10)
        draw_bar(frame, QUALITY_NAMES, active_quality, 44)
    cv2.putText(frame, f"MODE: {mode.upper()}   (M = switch, W/S = chord octave)",
                (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)

    cv2.imshow("hands", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == 27:                       # Esc
        break
    elif key == ord('m'):
        mode = "chords" if mode == "notes" else "notes"
    elif key == ord('w'):
        chord_base = min(chord_base + 12, 72)
    elif key == ord('s'):
        chord_base = max(chord_base - 12, 36)

# ---------- Cleanup ----------
for n in sounding:
    out.send(mido.Message('note_off', note=n))
cap.release()
cv2.destroyAllWindows()