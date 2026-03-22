*Read this in: [English](README.md) | [Polski](README.pl.md)*

# Launchpad Mini MK3 – Pixel Art Editor

A web-based pixel art editor for the Novation Launchpad Mini MK3, with real-time hardware preview and a CLI toolset for animations and image conversion.

## Features

- **Web editor** (`index.html`) – draw pixel art on an 8×8 grid using the full 128-color Launchpad palette
- **Live preview** – see your artwork on the physical Launchpad in real time while editing
- **CLI player** (`launchpad_grid.py`) – play back animations and scenes on the hardware
- **PNG converter** (`png2launchpad.py`) – convert any PNG image to the Launchpad pixel art format

## Quick Start

1. Open `index.html` in a browser
2. Pick a color from the palette and draw on the grid
3. Save your work with the "Save" button (downloads a `.txt` file)

### Live Preview on Hardware

Connect your Launchpad Mini MK3 via USB, then:

```bash
# Install dependency
pip install pyyaml

# Start the live preview server (auto-detects MIDI port)
./launchpad_grid.py --serve

# Or specify a port manually
./launchpad_grid.py --serve -p hw:1,0,0
```

In the editor, click **"Live Preview"** – the button turns green and every edit is immediately sent to the Launchpad.

### Playing Animations

```bash
# Play an animation file
./launchpad_grid.py path/to/animation.txt

# Loop with custom FPS
./launchpad_grid.py -l --fps 12 animation.txt

# Show a single frame
./launchpad_grid.py -f 3 animation.txt

# Clear the display
./launchpad_grid.py --clear
```

### Playing Scenes (YAML)

```bash
./launchpad_grid.py --scene scene.yaml --loop
```

### Scrolling Text

```bash
# Scroll text once in white
./launchpad_grid.py --text "Hello World"

# Loop red text at speed 15
./launchpad_grid.py --text "Alert!" -l --speed 15 --color 5

# Custom RGB color
./launchpad_grid.py --text "RGB" --color 0,127,0

# Stop scrolling
./launchpad_grid.py --text-stop
```

### Converting PNG to Launchpad Format

```bash
python3 png2launchpad.py input.png output.txt
```

The image must be square (max 400×400 px). It is resized to 8×8 and each pixel is mapped to the nearest Launchpad palette color.

## Editor Tools

| Tool | Description |
|------|-------------|
| Brush | Draw with the selected color |
| Selection | Select cells (rectangle, ellipse, vertical/horizontal line) |
| Deselect | Clear current selection |
| Bucket Fill | Fill selected area or flood-fill |
| Color Picker | Pick a color from the grid |
| Eraser | Set cells to color 0 (off) |
| Clear Selection | Erase only selected cells |
| New Document | Clear the entire grid |

## File Format

The `.txt` file format is a simple text grid – 8 rows of 8 space-separated color indices (0–127):

```
# Launchpad Mini MK3 pixel art
delay 100
0 0 0 5 5 0 0 0
0 0 5 5 5 5 0 0
0 5 5 5 5 5 5 0
5 5 5 5 5 5 5 5
5 5 5 5 5 5 5 5
0 5 5 5 5 5 5 0
0 0 5 5 5 5 0 0
0 0 0 5 5 0 0 0
```

Multiple frames can be separated with `---` and different delays set with `delay <ms>`.

## CLI Reference

```
./launchpad_grid.py [options] [animation.txt]

Options:
  -p, --port PORT       MIDI port (e.g. hw:1,0,0). Auto-detected if omitted.
  -l, --loop            Loop playback indefinitely
  -n, --repeats N       Number of playback repeats (default: 1)
  -f, --frame N         Display only frame N
  --fps FPS             Override playback speed
  --clear               Clear the Launchpad display
  --list-ports          List available MIDI output ports
  --scene FILE          Load a YAML scene file
  --serve               Start HTTP server for live preview
  --http-port PORT      HTTP port for --serve (default: 9321)
  --text STRING         Scroll text across the Launchpad surface
  --text-stop           Stop any active text scroll
  --speed N             Scroll speed in pads/second (default: 10; negative = reverse)
  --color COLOR         Text color: palette index 0-127 or r,g,b (e.g. 127,0,0)
```

```
python3 png2launchpad.py [options] <input.png> [output.txt]

Options:
  -h, --help            Show help message and exit
```

## Requirements

- Python 3.9+
- `pyyaml` (`pip install pyyaml`)
- `amidi` (part of `alsa-utils` on Linux)
- Novation Launchpad Mini MK3
