from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import mido
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'midi-chord-helper'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# (suffix, sorted pitch-class intervals)
CHORD_PATTERNS = [
    ('',      [0, 4, 7]),
    ('m',     [0, 3, 7]),
    ('7',     [0, 4, 7, 10]),
    ('maj7',  [0, 4, 7, 11]),
    ('m7',    [0, 3, 7, 10]),
    ('dim',   [0, 3, 6]),
    ('aug',   [0, 4, 8]),
    ('m7b5',  [0, 3, 6, 10]),
    ('dim7',  [0, 3, 6, 9]),
    ('sus4',  [0, 5, 7]),
    ('sus2',  [0, 2, 7]),
    ('add9',  [0, 2, 4, 7]),
    ('6',     [0, 4, 7, 9]),
    ('m6',    [0, 3, 7, 9]),
]

MAJOR_IVS = [0, 2, 4, 5, 7, 9, 11]
MINOR_IVS = [0, 2, 3, 5, 7, 8, 10]
MAJOR_Q   = ['', 'm', 'm', '', '', 'm', 'dim']
MAJOR_D   = ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°']
MINOR_Q   = ['m', 'dim', '', 'm', 'm', '', '']
MINOR_D   = ['i', 'ii°', 'III', 'iv', 'v', 'VI', 'VII']

active_notes = set()
recorded_chords = []  # list of sorted note lists
midi_thread = None
auto_capture = False
peak_notes = set()   # largest simultaneous note set since last all-notes-off


def note_name(midi_num):
    return NOTE_NAMES[midi_num % 12]


def detect_chord(notes):
    if len(notes) < 2:
        return None
    pcs = sorted(set(n % 12 for n in notes))
    if len(pcs) < 2:
        return None
    best, best_score = None, -1
    for root in pcs:
        ivs = sorted((p - root) % 12 for p in pcs)
        for suffix, pattern in CHORD_PATTERNS:
            if ivs == sorted(p % 12 for p in pattern):
                score = len(pattern) * 10 - len(suffix)
                if score > best_score:
                    best_score = score
                    best = f"{NOTE_NAMES[root]}{suffix}"
    return best


def detect_key(chord_list):
    all_pcs = set()
    for notes in chord_list:
        for n in notes:
            all_pcs.add(n % 12)
    best, best_score = (0, 'major'), -999
    for tonic in range(12):
        for mode, ivs in [('major', MAJOR_IVS), ('minor', MINOR_IVS)]:
            scale = set((tonic + i) % 12 for i in ivs)
            score = len(all_pcs & scale) - len(all_pcs - scale)
            if score > best_score:
                best_score = score
                best = (tonic, mode)
    return best


def build_suggestions(chord_list):
    tonic, mode = detect_key(chord_list)
    t = NOTE_NAMES[tonic]
    ivs      = MAJOR_IVS if mode == 'major' else MINOR_IVS
    qualities = MAJOR_Q  if mode == 'major' else MINOR_Q
    degrees   = MAJOR_D  if mode == 'major' else MINOR_D

    diatonic = []
    for interval, q, deg in zip(ivs, qualities, degrees):
        root = NOTE_NAMES[(tonic + interval) % 12]
        diatonic.append({'chord': f"{root}{q}", 'degree': deg})

    scale_notes = [NOTE_NAMES[(tonic + i) % 12] for i in ivs]

    extras = []
    v7 = NOTE_NAMES[(tonic + 7) % 12]
    extras.append({'chord': f"{v7}7", 'why': 'Dominant 7 — strong pull back to the root'})
    if mode == 'major':
        ii = NOTE_NAMES[(tonic + 2) % 12]
        extras.append({'chord': f"{ii}m7", 'why': 'ii7 — smooth jazz color, leads nicely to V'})
        iv = NOTE_NAMES[(tonic + 5) % 12]
        extras.append({'chord': f"{iv}maj7", 'why': 'IVmaj7 — dreamy, open feeling'})
    else:
        iv = NOTE_NAMES[(tonic + 5) % 12]
        extras.append({'chord': f"{iv}m7", 'why': 'iv7 — deep, melancholic color'})
        vi = NOTE_NAMES[(tonic + 8) % 12]
        extras.append({'chord': f"{vi}maj7", 'why': 'VImaj7 — bright contrast in a minor key'})

    return {
        'key': f"{t} {mode}",
        'scale_notes': scale_notes,
        'diatonic_chords': diatonic,
        'extra_chords': extras,
    }


def do_capture(notes):
    recorded_chords.append(notes[:])
    chord_name = detect_chord(notes) or '?'
    idx = len(recorded_chords) - 1
    socketio.emit('captured', {
        'idx': idx,
        'chord': chord_name,
        'notes': [note_name(n) for n in notes],
        'count': len(recorded_chords),
    })


def midi_listener(port_name):
    global active_notes, auto_capture, peak_notes
    try:
        with mido.open_input(port_name) as port:
            socketio.emit('status', {'ok': True, 'msg': f'Connected to {port_name}'})
            for msg in port:
                if msg.type == 'note_on' and msg.velocity > 0:
                    active_notes.add(msg.note)
                    # Track the largest chord held so far in this gesture
                    if auto_capture and len(active_notes) > len(peak_notes):
                        peak_notes = active_notes.copy()
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    active_notes.discard(msg.note)
                else:
                    continue

                # Auto-capture: fire when all keys are released after holding a chord
                if auto_capture and len(active_notes) == 0 and len(peak_notes) >= 2:
                    do_capture(sorted(peak_notes))
                    peak_notes = set()

                notes_list = sorted(active_notes)
                chord = detect_chord(notes_list) if len(notes_list) >= 2 else None
                socketio.emit('note_update', {
                    'notes': notes_list,
                    'names': [note_name(n) for n in notes_list],
                    'chord': chord,
                })
    except Exception as e:
        socketio.emit('status', {'ok': False, 'msg': f'MIDI error: {e}'})


@app.route('/')
def index():
    ports = mido.get_input_names()
    return render_template('index.html', ports=ports)


@socketio.on('get_ports')
def on_get_ports():
    emit('ports', {'ports': mido.get_input_names()})


@socketio.on('connect_midi')
def on_connect_midi(data):
    global midi_thread
    port = data.get('port', '')
    if not port:
        emit('status', {'ok': False, 'msg': 'No port selected'})
        return
    midi_thread = threading.Thread(target=midi_listener, args=(port,), daemon=True)
    midi_thread.start()


@socketio.on('start_auto_capture')
def on_start_auto_capture():
    global auto_capture, peak_notes
    auto_capture = True
    peak_notes = set()
    socketio.emit('auto_capture_started')


@socketio.on('analyze')
def on_analyze():
    if len(recorded_chords) < 2:
        emit('capture_err', {'msg': 'Record at least 2 chords before analyzing'})
        return
    emit('analysis', build_suggestions(recorded_chords))


@socketio.on('stop_auto_capture')
def on_stop_auto_capture():
    global auto_capture
    auto_capture = False
    socketio.emit('auto_capture_stopped')


@socketio.on('clear')
def on_clear():
    global recorded_chords, auto_capture, peak_notes
    recorded_chords = []
    auto_capture = False
    peak_notes = set()
    socketio.emit('cleared')


if __name__ == '__main__':
    print('\n  MIDI Chord Helper is running!')
    print('  Open this in your browser: http://localhost:5001\n')
    socketio.run(app, host='127.0.0.1', port=5001, debug=False,
                 use_reloader=False, allow_unsafe_werkzeug=True)
