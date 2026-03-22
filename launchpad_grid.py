#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import threading
import time

import yaml


COLOR_MAP = {
    ".": 0,
    "r": 5,
    "g": 19,
    "b": 45,
    "y": 13,
    "o": 9,
    "w": 3,
    "c": 37,
    "p": 53,
}
NAME_TO_TOKEN = {
    "red": "r",
    "green": "g",
    "blue": "b",
    "yellow": "y",
    "orange": "o",
    "white": "w",
    "cyan": "c",
    "pink": "p",
}
SCENE_COLORS = set(NAME_TO_TOKEN)
BASIC_COLOR_SEQUENCE = list(NAME_TO_TOKEN)

FUNCTION_INDICES = [19, 29, 39, 49, 59, 69, 79, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99]
GRID_INDICES = [
    [81, 82, 83, 84, 85, 86, 87, 88],
    [71, 72, 73, 74, 75, 76, 77, 78],
    [61, 62, 63, 64, 65, 66, 67, 68],
    [51, 52, 53, 54, 55, 56, 57, 58],
    [41, 42, 43, 44, 45, 46, 47, 48],
    [31, 32, 33, 34, 35, 36, 37, 38],
    [21, 22, 23, 24, 25, 26, 27, 28],
    [11, 12, 13, 14, 15, 16, 17, 18],
]


@dataclass(frozen=True)
class Frame:
    rows: list[list[str]]
    delay_ms: int


@dataclass(frozen=True)
class Animation:
    frames: list[Frame]
    default_delay_ms: int


@dataclass(frozen=True)
class Motion:
    dx: int
    dy: int
    bounds: str
    on_bounce: str | None = None


@dataclass(frozen=True)
class PixelObject:
    object_id: str
    x: int
    y: int
    color: str
    motion: Motion


@dataclass(frozen=True)
class Scene:
    fps: int
    width: int
    height: int
    objects: list[PixelObject]


@dataclass(frozen=True)
class MidiPort:
    direction: str
    port: str
    name: str


def positive_fps(value: str) -> float:
    fps = float(value)
    if fps <= 0:
        raise argparse.ArgumentTypeError("--fps must be greater than 0")
    return fps


def parse_animation(text: str) -> Animation:
    default_delay_ms = 100
    current_delay_ms = default_delay_ms
    pending_rows: list[list[str]] = []
    frames: list[Frame] = []

    def finalize_frame() -> None:
        nonlocal pending_rows
        if not pending_rows:
            return
        if len(pending_rows) != 8:
            raise ValueError("Each frame must contain exactly 8 rows")
        frames.append(Frame(rows=pending_rows, delay_ms=current_delay_ms))
        pending_rows = []

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "---":
            finalize_frame()
            continue
        if line.startswith("delay "):
            finalize_frame()
            current_delay_ms = int(line.split()[1])
            if not frames and not pending_rows:
                default_delay_ms = current_delay_ms
            continue

        tokens = line.split()
        if len(tokens) != 8:
            raise ValueError("Each frame row must contain exactly 8 columns")
        for token in tokens:
            if token not in COLOR_MAP and not token.isdigit():
                raise ValueError(f"Unknown color token: {token}")
            if token.isdigit() and not 0 <= int(token) <= 127:
                raise ValueError(f"Palette index out of range: {token}")
        pending_rows.append(tokens)
        if len(pending_rows) > 8:
            raise ValueError("Each frame must contain exactly 8 rows")

    finalize_frame()
    if not frames:
        raise ValueError("Animation must contain at least one frame")
    return Animation(frames=frames, default_delay_ms=default_delay_ms)


def color_value(token: str) -> int:
    return COLOR_MAP[token] if token in COLOR_MAP else int(token)


def ensure_keys(data: dict, allowed: set[str], label: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"{label}: unknown field '{sorted(unknown)[0]}'")


def require_int(value: object, label: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    return value


def parse_scene(text: str) -> Scene:
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError("scene file must be a YAML mapping")
    ensure_keys(loaded, {"scene", "objects"}, "root")
    if "scene" not in loaded or "objects" not in loaded:
        raise ValueError("scene file must define 'scene' and 'objects'")

    scene_data = loaded["scene"]
    if not isinstance(scene_data, dict):
        raise ValueError("scene must be a mapping")
    ensure_keys(scene_data, {"fps", "width", "height"}, "scene")

    fps = require_int(scene_data.get("fps"), "scene.fps")
    width = require_int(scene_data.get("width"), "scene.width")
    height = require_int(scene_data.get("height"), "scene.height")
    if fps <= 0:
        raise ValueError("scene.fps must be greater than 0")
    if width != 8 or height != 8:
        raise ValueError("scene.width and scene.height must both equal 8")

    objects_data = loaded["objects"]
    if not isinstance(objects_data, list) or not objects_data:
        raise ValueError("objects must be a non-empty list")

    objects: list[PixelObject] = []
    seen_ids: set[str] = set()
    for index, obj in enumerate(objects_data):
        label = f"object[{index}]"
        if not isinstance(obj, dict):
            raise ValueError(f"{label} must be a mapping")
        ensure_keys(obj, {"id", "type", "x", "y", "color", "motion"}, label)

        object_id = obj.get("id")
        if not isinstance(object_id, str) or not object_id:
            raise ValueError(f"{label}.id must be a non-empty string")
        if object_id in seen_ids:
            raise ValueError(f"duplicate object id '{object_id}'")
        seen_ids.add(object_id)

        if obj.get("type") != "pixel":
            raise ValueError(f"object '{object_id}': unsupported type '{obj.get('type')}'")
        x = require_int(obj.get("x"), f"object '{object_id}': x")
        y = require_int(obj.get("y"), f"object '{object_id}': y")
        if not 0 <= x < width:
            raise ValueError(f"object '{object_id}': x must be between 0 and {width - 1}")
        if not 0 <= y < height:
            raise ValueError(f"object '{object_id}': y must be between 0 and {height - 1}")

        color = obj.get("color")
        if color not in SCENE_COLORS:
            raise ValueError(f"object '{object_id}': unsupported color '{color}'")

        motion_data = obj.get("motion")
        if not isinstance(motion_data, dict):
            raise ValueError(f"object '{object_id}': motion must be a mapping")
        ensure_keys(motion_data, {"dx", "dy", "bounds", "on_bounce"}, f"object '{object_id}'.motion")
        dx = require_int(motion_data.get("dx"), f"object '{object_id}': dx")
        dy = require_int(motion_data.get("dy"), f"object '{object_id}': dy")
        bounds = motion_data.get("bounds")
        if bounds not in {"bounce", "wrap"}:
            raise ValueError(f"object '{object_id}': unsupported bounds '{bounds}'")
        on_bounce = motion_data.get("on_bounce")
        if on_bounce is not None and on_bounce != "random_color":
            raise ValueError(f"object '{object_id}': unsupported on_bounce '{on_bounce}'")
        if on_bounce is not None and bounds != "bounce":
            raise ValueError(f"object '{object_id}': on_bounce requires bounds 'bounce'")

        objects.append(
            PixelObject(
                object_id=object_id,
                x=x,
                y=y,
                color=color,
                motion=Motion(dx=dx, dy=dy, bounds=bounds, on_bounce=on_bounce),
            )
        )

    return Scene(fps=fps, width=width, height=height, objects=objects)


def render_scene(scene: Scene) -> Frame:
    rows = [["."] * scene.width for _ in range(scene.height)]
    for obj in scene.objects:
        rows[obj.y][obj.x] = NAME_TO_TOKEN[obj.color]
    return Frame(rows=rows, delay_ms=round(1000 / scene.fps))


def choose_random_color(current: str) -> str:
    options = [color for color in BASIC_COLOR_SEQUENCE if color != current]
    return random.choice(options)


def step_scene(scene: Scene) -> Scene:
    next_objects: list[PixelObject] = []
    for obj in scene.objects:
        x = obj.x + obj.motion.dx
        y = obj.y + obj.motion.dy
        dx = obj.motion.dx
        dy = obj.motion.dy
        bounced = False

        if obj.motion.bounds == "wrap":
            x %= scene.width
            y %= scene.height
        else:
            if x < 0 or x >= scene.width:
                dx = -dx
                x = obj.x + dx
                bounced = True
            if y < 0 or y >= scene.height:
                dy = -dy
                y = obj.y + dy
                bounced = True

        color = obj.color
        if bounced and obj.motion.on_bounce == "random_color":
            color = choose_random_color(color)

        next_objects.append(
            PixelObject(
                object_id=obj.object_id,
                x=x,
                y=y,
                color=color,
                motion=Motion(dx=dx, dy=dy, bounds=obj.motion.bounds, on_bounce=obj.motion.on_bounce),
            )
        )

    return Scene(fps=scene.fps, width=scene.width, height=scene.height, objects=next_objects)


def build_frame_sysex(frame: Frame) -> str:
    parts = ["F0", "00", "20", "29", "02", "0D", "03"]
    for row_index, row in enumerate(frame.rows):
        for col_index, token in enumerate(row):
            parts.extend(
                [
                    "00",
                    f"{GRID_INDICES[row_index][col_index]:02X}",
                    f"{color_value(token):02X}",
                ]
            )
    for index in FUNCTION_INDICES:
        parts.extend(["00", f"{index:02X}", "00"])
    parts.append("F7")
    return " ".join(parts)


def build_clear_sysex() -> str:
    return build_frame_sysex(Frame(rows=[["."] * 8 for _ in range(8)], delay_ms=0))


def parse_amidi_ports(text: str) -> list[MidiPort]:
    ports: list[MidiPort] = []
    pattern = re.compile(r"^\s*(IO|I|O)\s+(hw:\d+,\d+,\d+)\s+(.+?)\s*$")
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        direction, port, name = match.groups()
        ports.append(MidiPort(direction=direction, port=port, name=name))
    return ports


def list_midi_ports() -> list[MidiPort]:
    result = subprocess.run(["amidi", "-l"], check=True, capture_output=True, text=True)
    return parse_amidi_ports(result.stdout)


def supports_output(port: MidiPort) -> bool:
    return "O" in port.direction


def is_launchpad_port(port: MidiPort) -> bool:
    name = port.name.lower()
    return "launchpad" in name or ("novation" in name and "lp" in name)


def auto_detect_port() -> str:
    ports = [port for port in list_midi_ports() if supports_output(port)]
    launchpads = [port for port in ports if is_launchpad_port(port)]
    if len(launchpads) == 1:
        return launchpads[0].port
    if len(launchpads) > 1:
        candidates = ", ".join(f"{port.port} ({port.name})" for port in launchpads)
        raise ValueError(f"Multiple Launchpad ports detected: {candidates}")
    if not ports:
        raise ValueError("No MIDI output ports found. Check `amidi -l`.")
    available = ", ".join(f"{port.port} ({port.name})" for port in ports)
    raise ValueError(f"No Launchpad port detected automatically. Available MIDI output ports: {available}")


def resolve_port(args: argparse.Namespace) -> str:
    if args.port:
        return args.port
    return auto_detect_port()


def print_port_commands(script_name: str, ports: list[MidiPort]) -> None:
    output_ports = [port for port in ports if supports_output(port)]
    if not output_ports:
        print("No MIDI output ports found.")
        return
    for port in output_ports:
        print(f"{script_name} -p {port.port} --clear  # {port.name} [{port.direction}]")


def send_hex(port: str, hex_bytes: str) -> None:
    subprocess.run(["amidi", "-p", port, "-S", hex_bytes], check=True)


def send_programmer_mode(port: str) -> None:
    send_hex(port, "F0 00 20 29 02 0D 00 7F F7")


def parse_color_spec(value: str) -> list[int]:
    """Parse a color spec: palette index (0-127) or r,g,b (each 0-127)."""
    if "," in value:
        parts = value.split(",")
        if len(parts) != 3:
            raise argparse.ArgumentTypeError("RGB color must be r,g,b (e.g. 127,0,0)")
        rgb = []
        for component in parts:
            n = int(component)
            if not 0 <= n <= 127:
                raise argparse.ArgumentTypeError(f"RGB component must be 0-127, got {n}")
            rgb.append(n)
        return [0x01] + rgb
    idx = int(value)
    if not 0 <= idx <= 127:
        raise argparse.ArgumentTypeError(f"Palette index must be 0-127, got {idx}")
    return [0x00, idx]


def build_text_scroll_sysex(text: str, *, loop: bool = False,
                            speed: int = 10, color_bytes: list[int] | None = None) -> str:
    """Build SysEx message for text scrolling on Launchpad Mini MK3.

    speed: pads/second (1-63 left-to-right, negative for right-to-left)
    """
    header = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D, 0x07]
    payload = [1 if loop else 0]

    # Speed: positive = right-to-left scroll, negative = left-to-right
    # Values 0x40+ are interpreted as negative by the device
    if speed < 0:
        speed_byte = (abs(speed) + 0x80) & 0x7F  # map to 0x40+
    else:
        speed_byte = speed & 0x3F
    payload.append(speed_byte)

    if color_bytes is None:
        color_bytes = [0x00, 0x03]  # palette white
    payload.extend(color_bytes)

    payload.extend(ord(c) for c in text)
    parts = header + payload + [0xF7]
    return " ".join(f"{b:02X}" for b in parts)


def build_text_stop_sysex() -> str:
    """Build SysEx to stop any active text scroll."""
    return "F0 00 20 29 02 0D 07 F7"


def build_grid_sysex(color_indices: list[int]) -> str:
    """Build SysEx from a flat list of 64 color indices (row-major, 0-127)."""
    parts = ["F0", "00", "20", "29", "02", "0D", "03"]
    for row in range(8):
        for col in range(8):
            idx = row * 8 + col
            color = max(0, min(127, color_indices[idx]))
            parts.extend(["00", f"{GRID_INDICES[row][col]:02X}", f"{color:02X}"])
    for fi in FUNCTION_INDICES:
        parts.extend(["00", f"{fi:02X}", "00"])
    parts.append("F7")
    return " ".join(parts)


class LiveHandler(BaseHTTPRequestHandler):
    """HTTP handler for live preview – accepts POST /grid with JSON body."""

    midi_port: str = ""

    def do_POST(self) -> None:
        if self.path != "/grid":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            colors = data["grid"]
            if not isinstance(colors, list) or len(colors) != 64:
                raise ValueError("grid must be a list of 64 integers")
            sysex = build_grid_sysex(colors)
            send_hex(self.midi_port, sysex)
        except Exception as exc:
            self.send_response(500)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(str(exc).encode())
            return
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        print(fmt % args, flush=True)


def run_serve(args: argparse.Namespace) -> int:
    port = resolve_port(args)
    send_programmer_mode(port)
    send_hex(port, build_clear_sysex())

    LiveHandler.midi_port = port
    http_port = args.http_port
    server = HTTPServer(("0.0.0.0", http_port), LiveHandler)
    print(f"Live preview server running on http://localhost:{http_port}")
    print(f"MIDI port: {port}")
    print("Open the editor in a browser and click 'Live Preview' to connect.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        send_hex(port, build_clear_sysex())
        server.server_close()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Launchpad Mini MK3 – CLI tool for rendering pixel art, animations "
            "and scenes on the hardware. Can also serve as a live preview bridge "
            "for the web-based pixel art editor (index.html)."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s demo.txt                   Play an animation file\n"
            "  %(prog)s -l --fps 12 demo.txt        Loop at 12 FPS\n"
            "  %(prog)s --scene scene.yaml --loop    Play a YAML scene\n"
            "  %(prog)s --serve                      Start live preview server\n"
            "  %(prog)s --clear                      Clear the Launchpad display\n"
            "  %(prog)s --list-ports                 Show available MIDI ports\n"
            "  %(prog)s --text 'Hello!'              Scroll text once\n"
            "  %(prog)s --text 'Hi' -l --color 5     Scroll red text in a loop\n"
            "  %(prog)s --text 'RGB' --color 0,127,0 Scroll with custom RGB color\n"
            "  %(prog)s --text-stop                  Stop active text scroll"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", metavar="FILE",
                        help="animation file to play (.txt)")
    parser.add_argument("--scene", metavar="FILE",
                        help="load a YAML scene file")
    parser.add_argument("-p", "--port", metavar="PORT",
                        help="MIDI port (e.g. hw:1,0,0); auto-detected if omitted")
    parser.add_argument("-l", "--loop", action="store_true",
                        help="loop playback indefinitely")
    parser.add_argument("-n", "--repeats", type=int, default=1, metavar="N",
                        help="number of playback repeats (default: 1)")
    parser.add_argument("-f", "--frame", type=int, metavar="N",
                        help="display only frame N (1-based)")
    parser.add_argument("--fps", type=positive_fps,
                        help="override playback speed")
    parser.add_argument("--clear", action="store_true",
                        help="clear the Launchpad display")
    parser.add_argument("--list-ports", action="store_true",
                        help="list available MIDI output ports")
    parser.add_argument("--serve", action="store_true",
                        help="start HTTP server for live preview from the web editor")
    parser.add_argument("--http-port", type=int, default=9321, metavar="PORT",
                        help="HTTP port for --serve mode (default: 9321)")
    parser.add_argument("--text", metavar="STRING",
                        help="scroll text across the Launchpad surface")
    parser.add_argument("--text-stop", action="store_true",
                        help="stop any active text scroll")
    parser.add_argument("--speed", type=int, default=10, metavar="N",
                        help="scroll speed in pads/second (default: 10; negative = reverse)")
    parser.add_argument("--color", metavar="COLOR",
                        help="text color: palette index 0-127 or r,g,b (e.g. 127,0,0)")
    return parser.parse_args(argv)


def load_animation(path: str) -> Animation:
    return parse_animation(Path(path).read_text())


def load_scene(path: str) -> Scene:
    return parse_scene(Path(path).read_text())


def effective_delay(frame: Frame, fps: float | None) -> float:
    if fps:
        return 1.0 / fps
    return frame.delay_ms / 1000.0


def run_animation(args: argparse.Namespace) -> int:
    port = resolve_port(args)
    send_programmer_mode(port)

    if args.clear:
        send_hex(port, build_clear_sysex())
        return 0

    if args.scene:
        if args.path:
            raise ValueError("Animation file path cannot be used together with --scene")
        if args.frame is not None:
            raise ValueError("Frame selection is not supported with --scene")
        scene = load_scene(args.scene)
        if args.fps:
            scene = Scene(fps=round(args.fps), width=scene.width, height=scene.height, objects=scene.objects)
        loops = sys.maxsize if args.loop else args.repeats
        current_scene = scene
        for _ in range(loops):
            frame = render_scene(current_scene)
            send_hex(port, build_frame_sysex(frame))
            time.sleep(effective_delay(frame, args.fps))
            current_scene = step_scene(current_scene)
        return 0

    if not args.path:
        raise ValueError("Animation file path is required unless --clear is used")

    animation = load_animation(args.path)
    frames = animation.frames

    if args.frame is not None:
        index = args.frame - 1
        if not 0 <= index < len(frames):
            raise ValueError("Frame number out of range")
        send_hex(port, build_frame_sysex(frames[index]))
        return 0

    loops = sys.maxsize if args.loop else args.repeats
    for _ in range(loops):
        for frame in frames:
            send_hex(port, build_frame_sysex(frame))
            time.sleep(effective_delay(frame, args.fps))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.list_ports:
            print_port_commands("./launchpad_grid.py", list_midi_ports())
            return 0
        if args.serve:
            return run_serve(args)
        if args.text_stop:
            port = resolve_port(args)
            send_hex(port, build_text_stop_sysex())
            return 0
        if args.text is not None:
            port = resolve_port(args)
            color_bytes = parse_color_spec(args.color) if args.color else None
            sysex = build_text_scroll_sysex(
                args.text, loop=args.loop, speed=args.speed,
                color_bytes=color_bytes,
            )
            send_hex(port, sysex)
            return 0
        return run_animation(args)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
