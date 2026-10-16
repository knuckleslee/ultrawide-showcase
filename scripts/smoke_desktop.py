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
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WINDOWS = 13
INITIAL_SCENE = {"news", "chat", "video", "calendar", "notes"}
SCENES = {"daily", "editing", "coding", "gaming"}
EDITING_WINDOWS = {"premiere"}
CODING_WINDOWS = {"aiagent", "editor", "git", "terminal"}
GAMING_WINDOWS = {"discord", "game", "bahamut"}
PREMIERE_PANELS = {"effects", "source", "program", "project", "timeline", "meter", "scopes", "markers"}


class DesktopParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.windows: dict[str, set[str]] = {}
        self.scenes: set[str] = set()
        self.youtube_sources: list[str] = []
        self.premiere_panels: set[str] = set()
        self.monitor_dimensions: list[tuple[float, float]] = []
        self.monitor_aux_panels: list[str] = []
        self.premiere_layouts: set[str] = set()
        self.premiere_panel_order: list[str] = []
        self.premiere_top_rows = 0
        self.daily_recommendations = 0
        self.daily_contacts = 0
        self.daily_todos: list[str] = []
        self.daily_stories = 0
        self.calendar_controls: set[str] = set()
        self.news_reader_present = False
        self.calendar_dates = 0
        self.actor_classes: set[str] = set()
        self.demo_play_buttons = 0
        self.effect_dividers = 0
        self.cursor_tip_pulses = 0
        self.interactive_check = ""
        self.game_sources: list[str] = []
        self.game_poster_sources: list[str] = []
        self.game_poster_buttons = 0
        self.game_player_slots = 0
        self.game_start_seconds = ""
        self.game_video_id = ""
        self.game_interactive_check = ""
        self.github_font_modes: set[str] = set()
        self.coding_features: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        classes = set((data.get("class") or "").split())
        if tag == "html":
            self.interactive_check = data.get("data-interactive-check") or ""
            self.game_interactive_check = data.get("data-game-interactive-check") or ""
        if data.get("id") == "gamingVideoHost":
            self.game_start_seconds = data.get("data-start-seconds") or ""
            self.game_video_id = data.get("data-video-id") or ""
        if data.get("id") == "gamingPlayer":
            self.game_player_slots += 1
        if tag == "button" and data.get("id") == "gameResumeButton":
            self.game_poster_buttons += 1
        if tag == "img" and "game-poster-image" in classes:
            self.game_poster_sources.append(data.get("src") or "")
        if "pp-actor-one" in classes or "pp-actor-two" in classes:
            self.actor_classes.update(c for c in ("pp-actor-one", "pp-actor-two") if c in classes)
        if "pp-demo-play" in classes:
            self.demo_play_buttons += 1
        if "pp-fx-splitter" in classes:
            self.effect_dividers += 1
        if "tip-pulse" in classes:
            self.cursor_tip_pulses += 1
        if "yt-suggestion" in classes and data.get("data-rec-index") is not None:
            self.daily_recommendations += 1
        if "messenger-contact" in classes:
            self.daily_contacts += 1
        if "todo-check" in classes:
            self.daily_todos.append(data.get("aria-checked") or "")
        if "story" in classes and data.get("data-news-index") is not None:
            self.daily_stories += 1
        if "news-article" in classes and data.get("id") == "newsArticle":
            self.news_reader_present = True
        if tag == "button" and ("cal-prev" in classes or "cal-next" in classes):
            self.calendar_controls.add(next(c for c in ("cal-prev", "cal-next") if c in classes))
        if "cal-days" in classes:
            self.calendar_dates += 1
        if "pp-top" in classes:
            self.premiere_top_rows += 1
        for name in ("pp-edit-left", "pp-bottom-left", "pp-program-scopes"):
            if name in classes:
                self.premiere_layouts.add(name)
        if "pp-monitor-aux" in classes:
            self.monitor_aux_panels.append(data.get("class") or "")
        if "pp-monitor-shot" in classes:
            inline = data.get("style") or ""
            w = re.search(r"(?:^|;)\s*width:\s*([\d.]+)px", inline)
            h = re.search(r"(?:^|;)\s*height:\s*([\d.]+)px", inline)
            if w and h:
                self.monitor_dimensions.append((float(w.group(1)), float(h.group(1))))
        if data.get("data-pp-panel"):
            self.premiere_panels.add(data["data-pp-panel"])
            self.premiere_panel_order.append(data["data-pp-panel"])
        if tag == "iframe" and data.get("id") == "gamingFrame":
            self.game_sources.append(data.get("src") or "")
        if data.get("data-font-mode"):
            self.github_font_modes.add(data["data-font-mode"])
        for label in ("agentQuestion", "agentThinking", "agentSteps", "agentCodeChanges",
                      "codingScroll", "gitLiveScroll", "realCodeLines", "gitLiveFiles"):
            if data.get("id") == label:
                self.coding_features.add(label)
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
    if parser.daily_recommendations != 12:
        problems.append(f"Expected 12 scrollable YouTube recommendations, got {parser.daily_recommendations}")
    if parser.daily_contacts < 12:
        problems.append(f"Expected a scrollable chat list, got {parser.daily_contacts} contacts")
    if parser.daily_stories < 10 or not parser.news_reader_present:
        problems.append("Daily news requires 10+ clickable stories and an article reader")
    if parser.daily_todos != ["true", "true", "false", "false", "false"]:
        problems.append("Daily to-do checkboxes were not initialized correctly")
    if parser.calendar_controls != {"cal-prev", "cal-next"} or parser.calendar_dates != 1:
        problems.append("Calendar pagination controls or generated day grid missing")

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
            problems.append("Expected an upper-left dock with Effect Controls and Source")
        if editing_parser.premiere_panel_order[:2] != ["effects", "source"]:
            problems.append("Upper-left area must contain Effect Controls followed by Source")
        if not {"pp-edit-left", "pp-bottom-left", "pp-program-scopes"}.issubset(editing_parser.premiere_layouts):
            problems.append("Missing 60/40 editing split or useful Lumetri Scopes")
        if editing_parser.monitor_aux_panels:
            problems.append("Obsolete per-monitor metadata panels remain")
        if "markers" not in editing_parser.premiere_panel_order:
            problems.append("Source marker panel missing from unused upper-left space")
        if editing_parser.actor_classes != {"pp-actor-one", "pp-actor-two"}:
            problems.append("Both simulated musicians must have independently animated poses")
        if editing_parser.demo_play_buttons != 1 or editing_parser.effect_dividers != 1:
            problems.append("Premiere playback or draggable Effect Controls splitter missing")
        if editing_parser.cursor_tip_pulses != 1:
            problems.append("Arrow-tip click highlight must exist")
        if len(editing_parser.monitor_dimensions) != 2:
            problems.append("Source and Program media dimensions were not assigned")
        for width, height in editing_parser.monitor_dimensions:
            if width < 120 or height < 60:
                problems.append(f"Premiere media frame unexpectedly small: {width:.1f}x{height:.1f}")
            if not height or abs(width / height - 16 / 9) > .012:
                problems.append(f"Monitor media ratio should be 16:9, received {width}x{height}")
        if len(editing_parser.monitor_dimensions) == 2:
            (source_w,source_h),(program_w,program_h)=editing_parser.monitor_dimensions
            if program_w < source_w*1.65 or program_h < source_h*1.65:
                problems.append("Right Program must be substantially larger than upper-left Source")
            if program_w < 360 or program_h < 200:
                problems.append(f"Program preview insufficient for right-hand 40% workspace: {program_w}x{program_h}")


    # Confirm that the revamped 03 layout has 4 real windows, full-source/editor
    # scrolling, a scripted five-step AI response and five scoped uppercase modes.
    for scene_name, expected in (("coding", CODING_WINDOWS), ("gaming", GAMING_WINDOWS)):
        scene_dom = subprocess.run(
            command[:-1] + [source + "?scene=" + scene_name],
            text=True, capture_output=True, timeout=35,
        )
        if scene_dom.returncode != 0:
            problems.append(f"Chrome failed to render {scene_name} scene")
            continue
        scene_parser = DesktopParser()
        scene_parser.feed(scene_dom.stdout)
        visible_scene = {name for name, classes in scene_parser.windows.items()
                         if "offscreen" not in classes}
        if visible_scene != expected:
            problems.append(f"{scene_name} visible windows: {sorted(visible_scene)}")
        if scene_name == "coding":
            required_features = {"agentQuestion", "agentThinking", "agentSteps",
                                 "agentCodeChanges", "codingScroll", "gitLiveScroll",
                                 "realCodeLines", "gitLiveFiles"}
            if scene_parser.github_font_modes != {"XS", "SM", "MD", "LG", "XL"}:
                problems.append("GitHub 5 uppercase font modes XS/SM/MD/LG/XL missing")
            if not required_features.issubset(scene_parser.coding_features):
                problems.append("Coding AI AGENT/editor/live GitHub components missing")
        else:
            # No iframe is allowed before a Play request: thumbnail first, no loader.
            if scene_parser.game_sources:
                problems.append("Gaming player must be loaded lazily, not on entering scene")
            if scene_parser.game_start_seconds != "87" or scene_parser.game_video_id != "1or3YILu28M":
                problems.append("Gaming playback must start from 01:27 of the requested video")
            if scene_parser.game_poster_buttons != 1 or scene_parser.game_player_slots != 1:
                problems.append("Missing poster Play button or lazy YouTube player placeholder")
            if len(scene_parser.game_poster_sources) != 1 or (
                "i.ytimg.com/vi/1or3YILu28M/" not in scene_parser.game_poster_sources[0]
            ):
                problems.append("Original YouTube video thumbnail is not displayed")

    # Functional probe with the official YT.Player interface mocked locally.
    # This verifies thumbnail-first, Play from 87s, and restoring the poster,
    # without depending on browser autoplay permission or network access.
    game_probe_js = """
    <script>
    const poster=document.querySelector('#gameResumeButton');
    const initiallyVisible=!!poster && !poster.hidden;
    const lazyInitially=gameYTPlayer===null
      && !document.querySelector('#gamingVideoHost iframe');
    let videoId='',begin=0,seeked=0,destroyed=false;
    window.YT={
      PlayerState:{PLAYING:1,PAUSED:2,ENDED:0},
      Player:function(slot,options){
        videoId=options.videoId;
        begin=options.playerVars.start;
        const player={
          mute(){},
          seekTo(time){seeked=time},
          playVideo(){options.events.onStateChange({data:1,target:player})},
          destroy(){destroyed=true}
        };
        queueMicrotask(()=>options.events.onReady({target:player}));
        return player;
      }
    };
    poster?.click();
    setTimeout(()=>{
      const started=videoId==='1or3YILu28M'&&begin===87&&seeked===87
        && !!poster.hidden && gameWantsPlaying;
      resetGameVideo();
      const restored=!poster.hidden&&!gameWantsPlaying&&destroyed
        && !!document.querySelector('#gamingPlayer');
      document.documentElement.setAttribute('data-game-interactive-check',
        initiallyVisible&&lazyInitially&&started&&restored?'pass':
        'fail:'+JSON.stringify({initiallyVisible,lazyInitially,started,restored,begin,seeked,videoId}));
    },250);
    </script>
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            probe_page = Path(temp_dir) / "index.html"
            original = (ROOT / "index.html").read_text(encoding="utf-8")
            probe_page.write_text(original.replace("</body>", game_probe_js + "</body>"), encoding="utf-8")
            response = subprocess.run(
                command[:-1] + ["--virtual-time-budget=2400", probe_page.as_uri()+"?scene=gaming"],
                text=True, capture_output=True, timeout=35,
            )
            game_parser = DesktopParser()
            game_parser.feed(response.stdout)
            if response.returncode != 0 or game_parser.game_interactive_check != "pass":
                problems.append("Gaming thumbnail/playback browser probe: "
                                + (game_parser.game_interactive_check or "no response"))
                print("Gaming probe diagnostics:", response.stderr[-1500:], file=sys.stderr)
    except subprocess.TimeoutExpired:
        problems.append("Gaming thumbnail/playback browser probe timed out")

    # Functional browser probe: really click the Premiere transport button, let
    # the timecode progress, pause it, and verify the SVG arrow-tip coordinates.
    # A temporary HTML file keeps test code out of the deployed website.
    probe_js = """
    <script>
    const probeButton=document.querySelector('.pp-demo-play');
    const probeActor=document.querySelector('.pp-actor-one');
    const probeStarted=!!probeButton && (probeButton.click(), probeButton.getAttribute('aria-pressed')==='true');
    cursorAt(500,200,0);
    const probeTip=/translate3d\\(476px,\\s*186px/.test(document.querySelector('#guideCursor').style.transform);
    const probeBefore=document.querySelector('.pp-program .pp-timecode')?.textContent;
    setTimeout(()=>{
      const probeAfter=document.querySelector('.pp-program .pp-timecode')?.textContent;
      const probeAnimating=!!probeActor && getComputedStyle(probeActor).animationName.includes('pp-musician-one');
      if(probeButton)probeButton.click();
      const probeStopped=probeButton?.getAttribute('aria-pressed')==='false'
         && !document.querySelector('.pp-program')?.classList.contains('pp-is-playing');
      const gitPanel=document.querySelector('.live-github');
      const originalEditorSize=getComputedStyle(document.getElementById('codingScroll')).fontSize;
      setGitFontMode('XL');
      const isolatedFonts=gitPanel?.dataset.gitFont==='XL'
         && getComputedStyle(document.getElementById('codingScroll')).fontSize===originalEditorSize;
      const renderedMonth=document.querySelector('.cal-month-label')?.textContent;
      const rightMonth=(new Date().getMonth()+1);
      const calendarCurrent=renderedMonth?.includes(String(rightMonth)+' 月');
      document.documentElement.setAttribute('data-interactive-check',
        probeStarted && probeTip && probeBefore !== probeAfter && probeAnimating && probeStopped && isolatedFonts && calendarCurrent
        ? 'pass' : 'fail:'+JSON.stringify({probeStarted,probeTip,probeBefore,probeAfter,probeAnimating,probeStopped}));
    },1400);
    </script>
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            probe_page = Path(temp_dir) / "index.html"
            original = (ROOT / "index.html").read_text(encoding="utf-8")
            probe_page.write_text(original.replace("</body>", probe_js + "</body>"), encoding="utf-8")
            result_probe = subprocess.run(
                command[:-1] + ["--virtual-time-budget=4500", "--disable-background-timer-throttling",
                                probe_page.as_uri() + "?scene=editing"],
                text=True, capture_output=True, timeout=35,
            )
            test_parser = DesktopParser()
            test_parser.feed(result_probe.stdout)
            if result_probe.returncode != 0 or test_parser.interactive_check != "pass":
                problems.append("Interactive Premiere playback/cursor-tip probe: "
                                + (test_parser.interactive_check or "no response"))
                print("Interactive probe diagnostics:", result_probe.stderr[-2000:], file=sys.stderr)
    except subprocess.TimeoutExpired:
        problems.append("Interactive playback probe timed out")

    if problems:
        for problem in problems:
            print("ERROR:", problem, file=sys.stderr)
        print("Detected windows:", parser.windows, file=sys.stderr)
        print("Browser diagnostics:", result.stderr[-2500:], file=sys.stderr)
        return 1

    print(f"PASS: {len(parser.windows)} desktop windows created; "
          f"daily scene visible = {sorted(visible)}; four scene tabs present; "
          f"editing workspace includes {sorted(EDITING_WINDOWS)} and "
          f"{len(PREMIERE_PANELS)} docked Premiere panels; "
          f"large right Program preview at 16:9.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
