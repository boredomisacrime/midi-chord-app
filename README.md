# MIDI Chord Helper

A local web app that listens to your MIDI piano in real time, identifies the chords you're playing, and suggests notes, scales, and chords that work well with your progression.

![MIDI Chord Helper UI](screenshot.png)

## What it does

- Lights up a piano keyboard on screen as you play
- Detects and names chords in real time (major, minor, 7ths, sus, add9, and more)
- **Auto-capture mode** — just play and lift your hands between chords, no button pressing needed
- Record as many chords as you like (3, 5, 10 — whatever your progression is)
- Hit **Analyze** at any time to get:
  - The detected key (major or minor)
  - All the scale notes
  - Every diatonic chord that fits
  - A few extra "color chords" with explanations

## Requirements

- Mac with Python 3 installed (comes pre-installed on macOS)
- A MIDI piano connected via Bluetooth or USB — it just needs to show up in **Audio MIDI Setup** on your Mac

## How to run

```bash
bash run.sh
```

Then open **http://localhost:5001** in your browser.

That's it. The first run installs the dependencies automatically — after that it starts instantly.

## How to use

1. Make sure your MIDI piano is connected before opening the browser
2. Select your piano from the dropdown and click **Connect**
3. Click **Start Recording**
4. Play a chord with both hands, then lift all your fingers — it captures automatically
5. Repeat for as many chords as you want
6. Click **Analyze** to see what key you're in and what chords/notes fit

## Tech

- Python + Flask + Flask-SocketIO (backend, MIDI handling, music theory)
- Plain HTML/CSS/JS with Socket.IO (frontend)
- [mido](https://mido.readthedocs.io/) for reading MIDI input via CoreMIDI
