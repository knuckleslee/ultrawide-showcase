#!/usr/bin/env python3
"""Smoke test the real browser DOM to prevent successful but blank Pages deploys.

The test uses Google Chrome preinstalled on GitHub-hosted Ubuntu runners.
It verifies that JavaScript actually populated the desktop window layer.
"""
from __future__ import annotations

from html.parser import HTMLParser
import re
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WINDOWS = 15
INITIAL_SCENE = {"news", "chat", "video", "calendar", "notes"}
SCENES = {"daily", "editing", "coding", "gaming"}
EDITING_WINDOWS = {"premiere", "editnotes"}
PREMIERE_PANELS = {"effects", "source", "program", "project", "timeline", "meter"}


class DesktopParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.windows: dict[str, set[str]] = {}
        self.scenes: set[str] = set()
        self.youtube_sources: list[str] = []
        self.premiere_panels: set[str] = set()
        self.monitor_dimensions: list[tuple[float, float]] = []
        self.monitor_aux_panels: list[str] = []
        self.monitor_panel_widths: dict[str, float] = {}
        self.premiere_panel_order: list[str] = []
        self.premiere_top_rows = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        classes = set((data.get("class") or "").split())
        if "pp-top" in classes:
            self.premiere_top_rows += 1
        if "pp-monitor-aux" in classes:
            self.monitor_aux_panels.append(data.get("class") or "")
        if "pp-monitor" in classes and data.get("data-pp-panel") in ("source", "program"):
            value = re.search(r"(?:^|;)\s*width:\s*([\d.]+)px", data.get("style") or "")
            if value:
                self.monitor_panel_widths[data["data-pp-panel"]] = float(value.group(1))
        if "pp-monitor-shot" in classes:
            inline = data.get("style") or ""
            w = re.search(r"(?:^|;)\s*width:\s*([\d.]+)px", inline)
            h = re.search(r"(?:^|;)\s*height:\s*([\d.]+)px", inline)
            if w and h:
                self.monitor_dimensions.append((float(w.group(1)), float(h.group(1))))
        if data.get("data-pp-panel"):
            self.premiere_panels.add(data["data-pp-panel"])
            self.premiere_panel_order.append(data["data-pp-panel"])
        if tag == "iframe" and data.get("id") == "youtubeFrame":
            self.youtube_sources.append(data.get("src") or "")
        if tag == "button" and data.get("data-scene"):
            self.scenes.add(data["data-scene"])
        if tag == "article":
            classes = set((data.get("class") or "").split())
            if "window" in classes and data.get("data-id"):
                self.windows[data["data-id"]] = classes


def main() -> int:
    chrome = next((path for cmd in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
                   if (path := shutil.which(cmd))), None)
    if chrome is None:
        print("ERROR: Chrome/Chromium unavailable for browser smoke test", file=sys.stderr)
        return 1

    source = (ROOT / "index.html").resolve().as_uri()
    command = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--no-first-run", "--disable-extensions",
        "--virtual-time-budget=3500", "--dump-dom", source,
    ]
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=35)
    except subprocess.TimeoutExpired:
        print("ERROR: Browser timed out during desktop initialization", file=sys.stderr)
        return 1
    if result.returncode != 0:
        print("ERROR: Browser failed:", result.stderr[-2500:], file=sys.stderr)
        return 1

    parser = DesktopParser()
    parser.feed(result.stdout)

    visible = {name for name, classes in parser.windows.items()
               if "offscreen" not in classes}
    problems: list[str] = []
    if len(parser.windows) != EXPECTED_WINDOWS:
        problems.append(f"Expected {EXPECTED_WINDOWS} windows, found {len(parser.windows)}")
    if not INITIAL_SCENE.issubset(visible):
        problems.append(f"Missing visible daily windows: {sorted(INITIAL_SCENE - visible)}")
    if parser.scenes != SCENES:
        problems.append(f"Missing scene tabs: {sorted(SCENES - parser.scenes)}")
    if len(parser.youtube_sources) != 1 or "youtube-nocookie.com/embed/dQw4w9WgXcQ" not in parser.youtube_sources[0]:
        problems.append("Daily YouTube iframe missing or using the wrong video")

    # Load the real editing scene through the public ?scene=editing deep link.
    # This catches accidental regressions where the 02 workspace is blank.
    editing_result = subprocess.run(
        command[:-1] + [source + "?scene=editing"],
        text=True, capture_output=True, timeout=35,
    )
    if editing_result.returncode != 0:
        problems.append("Chrome failed to load editing scene")
        print("Editing browser diagnostics:", editing_result.stderr[-2500:], file=sys.stderr)
    else:
        editing_parser = DesktopParser()
        editing_parser.feed(editing_result.stdout)
        visible_editing = {name for name, classes in editing_parser.windows.items()
                           if "offscreen" not in classes}
        if visible_editing != EDITING_WINDOWS:
            problems.append(f"Editing scene windows mismatch: {sorted(visible_editing)}")
        if editing_parser.premiere_panels != PREMIERE_PANELS:
            problems.append(f"Premiere docked panels missing: "
                            f"{sorted(PREMIERE_PANELS - editing_parser.premiere_panels)}")
        if editing_parser.premiere_top_rows != 1:
            problems.append("Expected one common docked upper row")
        if editing_parser.premiere_panel_order[:3] != ["effects", "source", "program"]:
            problems.append("Top Premiere panels must be ordered Effect Controls, Source, Program")
        if editing_parser.monitor_aux_panels:
            problems.append("Extra monitor-side panels remain (gap must be consolidated at left)")
        if len(editing_parser.monitor_panel_widths) != 2:
            problems.append("Both monitor panel widths must be assigned at runtime")
        elif abs(editing_parser.monitor_panel_widths["source"] - editing_parser.monitor_panel_widths["program"]) > .8:
            problems.append("Source and Program panels have different widths")
        if len(editing_parser.monitor_dimensions) != 2:
            problems.append("Monitor media dimensions were not assigned on load")
        for width, height in editing_parser.monitor_dimensions:
            if width < 20 or height < 20 or abs(width / height - 16 / 9) > .012:
                problems.append(f"Monitor video ratio should be 16:9, received {width}x{height}")
        if len(editing_parser.monitor_dimensions) == 2:
            source_height, program_height = [d[1] for d in editing_parser.monitor_dimensions]
            if abs(source_height - program_height) > .8:
                problems.append("Source and Program media must retain identical original height")

    if problems:
        for problem in problems:
            print("ERROR:", problem, file=sys.stderr)
        print("Detected windows:", parser.windows, file=sys.stderr)
        print("Browser diagnostics:", result.stderr[-2500:], file=sys.stderr)
        return 1

    print(f"PASS: {len(parser.windows)} desktop windows created; "
          f"daily scene visible = {sorted(visible)}; four scene tabs present; "
          f"editing workspace includes {sorted(EDITING_WINDOWS)} and "
          f"{len(PREMIERE_PANELS)} docked Premiere panels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
