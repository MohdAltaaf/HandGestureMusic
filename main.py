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

NOTE_SIGNS = dict(zip(PATTERNS[:7], ROOTS[:7]))     # notes mode: C..B
ROOT_SIGNS = dict(zip(PATTERNS, ROOTS))             # chords mode, right hand
QUALITY_SIGNS = dict(zip(PATTERNS, QUALITIES))      # chords mode, left hand
DEGREE_SIGNS = dict(zip(PATTERNS[:7], range(7)))    # key mode: sign -> scale degree

# ---------- Music theory ----------
CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
QUALITY_NAMES = [q[0] for q in QUALITIES]
NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],     # natural minor
}

MODES = ["notes", "chords", "key"]
mode = "notes"
OCTAVE_BASES = {1: 48, 2: 60, 3: 72, 4: 84}
note_base = 60       # notes/key mode octave (left hand)
chord_base = 48      # chords mode octave (W / S keys)
key_root = 0         # 0 = C
scale_name = "major"


def diatonic_notes(degree, base=0):
    """Stack thirds on the scale: scale note, skip one, next, skip one, next."""
    scale = SCALES[scale_name]
    chord = []
    for step in (0, 2, 4):
        idx = degree + step
        chord.append(base + key_root + scale[idx % 7] + 12 * (idx // 7))
    return tuple(chord)


def chord_name(degree):
    n = diatonic_notes(degree)
    third, fifth = n[1] - n[0], n[2] - n[0]
    suffix = {(4, 7): "", (3, 7): "m", (3, 6): "dim"}.get((third, fifth), "?")
    return CHROMATIC[n[0] % 12] + suffix


# ---------- Interface ----------
FONT = cv2.FONT_HERSHEY_SIMPLEX
AMBER = (0, 184, 255)    # BGR
GREY = (80, 80, 80)
WHITE = (255, 255, 255)
LM_STYLE = draw.DrawingSpec(color=AMBER, thickness=2, circle_radius=2)
CONN_STYLE = draw.DrawingSpec(color=WHITE, thickness=1)


def draw_tabs(frame):
    for i, m in enumerate(MODES):
        x0 = 8 + i * 114
        on = (m == mode)
        cv2.rectangle(frame, (x0, 8), (x0 + 110, 32), AMBER if on else GREY, -1)
        cv2.putText(frame, f"{i + 1} {m.upper()}", (x0 + 10, 26), FONT, 0.5,
                    (0, 0, 0) if on else WHITE, 1)


def draw_bar(frame, names, active, y, bar_h=26):
    margin = 8
    cell = (frame.shape[1] - 2 * margin) // len(names)
    scale = 0.5 if len(names) <= 7 else 0.4
    for i, name in enumerate(names):
        x0 = margin + i * cell
        on = (name == active)
        cv2.rectangle(frame, (x0, y), (x0 + cell - 3, y + bar_h),
                      AMBER if on else GREY, -1)
        (tw, th), _ = cv2.getTextSize(name, FONT, scale, 1)
        cv2.putText(frame, name, (x0 + (cell - 3 - tw) // 2, y + (bar_h + th) // 2),
                    FONT, scale, (0, 0, 0) if on else WHITE, 1)


def label_box(frame, text, x, y):
    h, w, _ = frame.shape
    (tw, th), _ = cv2.getTextSize(text, FONT, 0.6, 2)
    x = max(4, min(x, w - tw - 8))
    y = max(th + 8, min(y, h - 4))
    cv2.rectangle(frame, (x - 4, y - th - 6), (x + tw + 4, y + 4), (30, 30, 30), -1)
    cv2.putText(frame, text, (x, y), FONT, 0.6, WHITE, 2)


def hand_text(label, states):
    if label == "Right":
        if states == FIST:
            return "rest"
        if mode == "notes":
            return NOTE_SIGNS.get(states, ("?",))[0]
        if mode == "chords":
            return ROOT_SIGNS.get(states, ("?",))[0]
        return chord_name(DEGREE_SIGNS[states]) if states in DEGREE_SIGNS else "?"
    if mode == "chords":
        return "Major" if states == FIST else QUALITY_SIGNS.get(states, ("?",))[0]
    return f"Octave {sum(states)}" if sum(states) in OCTAVE_BASES else "(keep)"


HINTS = {
    "notes":  "M or 1-2-3: mode | left hand: octave | Esc: quit",
    "chords": "M or 1-2-3: mode | W/S: octave | Esc: quit",
    "key":    "M or 1-2-3: mode | J/K: key | T: major/minor | Esc: quit",
}

# ---------- Sound state ----------
sounding = ()        # MIDI notes currently on
candidate = ()
stable_count = 0
STABLE_FRAMES = 0

# ---------- Main loop ----------
while True:
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    h, w, _ = frame.shape

    # darken the panels behind the text (after detection, so it can't hurt tracking)
    top_h = 106 if mode == "chords" else 74
    frame[0:top_h] = cv2.convertScaleAbs(frame[0:top_h], alpha=0.4)
    frame[h - 58:h] = cv2.convertScaleAbs(frame[h - 58:h], alpha=0.4)

    right = None    # finger pattern of the right hand, None if not seen
    left = None

    if result.multi_hand_landmarks:
        for lm, handed in zip(result.multi_hand_landmarks, result.multi_handedness):
            label = handed.classification[0].label
            states = finger_states(lm)
            if label == "Right":
                right = states
            else:
                left = states

            draw.draw_landmarks(frame, lm, mp.solutions.hands.HAND_CONNECTIONS,
                                landmark_drawing_spec=LM_STYLE,
                                connection_drawing_spec=CONN_STYLE)
            x = int(lm.landmark[0].x * w) - 30
            y = int(lm.landmark[0].y * h) + 35
            label_box(frame, f"{label}: {hand_text(label, states)}", x, y)

    # --- decide which notes we WANT right now ---
    # desired = tuple of MIDI notes, () for silence, None to hold (unknown sign)
    desired = None
    active = None       # highlighted cell in the first bar
    active2 = None      # highlighted cell in the second bar (chords mode)
    now_text = ""

    if mode in ("notes", "key") and left is not None and sum(left) in OCTAVE_BASES:
        note_base = OCTAVE_BASES[sum(left)]

    if mode == "notes":
        if right is None or right == FIST:
            desired = ()
        elif right in NOTE_SIGNS:
            name, offset = NOTE_SIGNS[right]
            desired = (note_base + offset,)
            active = now_text = name
        cur_base = note_base

    elif mode == "chords":
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
                active, active2 = root_name, quality[0]
                now_text = f"{root_name} {quality[0]}"
        cur_base = chord_base

    else:  # key mode
        if right is None or right == FIST:
            desired = ()
        elif right in DEGREE_SIGNS:
            degree = DEGREE_SIGNS[right]
            desired = diatonic_notes(degree, note_base - 12)
            active = now_text = chord_name(degree)
        cur_base = note_base - 12

    # --- stability filter + note on/off ---
    if desired is not None:
        if desired == candidate:
            stable_count += 1
        else:
            candidate = desired
            stable_count = 1

        if stable_count >= STABLE_FRAMES and candidate != sounding:
            for n in candidate:
                if n not in sounding:
                    out.send(mido.Message('note_on', note=n, velocity=VELOCITY))
            for n in sounding:
                if n not in candidate:
                    out.send(mido.Message('note_off', note=n))
            sounding = candidate

    # --- interface ---
    draw_tabs(frame)
    if mode == "notes":
        draw_bar(frame, NOTE_NAMES, active, 40)
    elif mode == "chords":
        draw_bar(frame, CHROMATIC, active, 40)
        draw_bar(frame, QUALITY_NAMES, active2, 72)
    else:
        draw_bar(frame, [chord_name(d) for d in range(7)], active, 40)
        cv2.putText(frame, f"Key: {CHROMATIC[key_root]} {scale_name}", (360, 26),
                    FONT, 0.6, AMBER, 2)

    if now_text:
        cv2.putText(frame, now_text, (14, h - 24), FONT, 1.0, AMBER, 2)
    else:
        cv2.putText(frame, "-", (14, h - 24), FONT, 1.0, GREY, 2)
    cv2.putText(frame, f"Octave {cur_base // 12 - 1}", (w - 130, h - 24),
                FONT, 0.6, WHITE, 1)
    cv2.putText(frame, HINTS[mode], (14, h - 8), FONT, 0.42, (200, 200, 200), 1)

    cv2.imshow("hands", frame)
    pressed = cv2.waitKey(1) & 0xFF
    if pressed == 27:                           # Esc
        break
    elif pressed == ord('m'):
        mode = MODES[(MODES.index(mode) + 1) % 3]
    elif pressed in (ord('1'), ord('2'), ord('3')):
        mode = MODES[pressed - ord('1')]
    elif pressed == ord('k'):
        key_root = (key_root + 1) % 12
    elif pressed == ord('j'):
        key_root = (key_root - 1) % 12
    elif pressed == ord('t'):
        scale_name = "minor" if scale_name == "major" else "major"
    elif pressed == ord('w'):
        chord_base = min(chord_base + 12, 72)
    elif pressed == ord('s'):
        chord_base = max(chord_base - 12, 36)

# ---------- Cleanup ----------
for n in sounding:
    out.send(mido.Message('note_off', note=n))
cap.release()
cv2.destroyAllWindows()