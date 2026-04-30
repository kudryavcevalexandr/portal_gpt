from pathlib import Path
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout

WORK_SECONDS = 180
BREAK_SECONDS = 60
TOTAL_ROUNDS = 8

KV = """
#:import dp kivy.metrics.dp

<TimerScreen>:
    orientation: "vertical"
    padding: dp(20)
    spacing: dp(12)
    canvas.before:
        Color:
            rgba: root.bg_color
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: root.status_text
        font_size: "36sp"
        bold: True
        size_hint_y: 0.2
        color: root.status_color

    Label:
        text: root.round_text
        font_size: "32sp"
        bold: True
        size_hint_y: 0.15

    Label:
        text: root.timer_text
        font_size: "96sp"
        bold: True
        size_hint_y: 0.35
        color: root.timer_color

    BoxLayout:
        size_hint_y: 0.3
        spacing: dp(8)

        Button:
            text: "START"
            on_release: root.start_training()
        Button:
            text: "PAUSE"
            on_release: root.pause_training()
        Button:
            text: "RESUME"
            on_release: root.resume_training()
        Button:
            text: "STOP"
            on_release: root.stop_training()
        Button:
            text: "RESET"
            on_release: root.reset_training()
"""


class TimerScreen(BoxLayout):
    time_left = NumericProperty(WORK_SECONDS)
    current_round = NumericProperty(1)
    is_break = BooleanProperty(False)
    started = BooleanProperty(False)
    paused = BooleanProperty(False)

    status_text = StringProperty("READY")
    round_text = StringProperty(f"ROUND 1 / {TOTAL_ROUNDS}")
    timer_text = StringProperty("03:00")

    bg_color = ListProperty([1, 1, 1, 1])
    timer_color = ListProperty([0.07, 0.07, 0.07, 1])
    status_color = ListProperty([0.07, 0.07, 0.07, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timer_event = None
        self.round_flash_schedule = set()
        self.round_duration = WORK_SECONDS
        self.ten_sec_played = False
        self.punch_reset_event = None
        self.start_sound = self._load_sound("start.mp3")
        self.end_sound = self._load_sound("end10.mp3")
        self.punch_sound = self._load_sound("punch.mp3")
        self.update_display()

    def _load_sound(self, filename):
        path = Path("static") / filename
        if path.exists():
            return SoundLoader.load(str(path))
        return None

    @staticmethod
    def _play(sound):
        if sound:
            try:
                sound.stop()
                sound.play()
            except Exception:
                pass

    @staticmethod
    def _format_time(seconds):
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def update_display(self):
        self.timer_text = self._format_time(self.time_left)
        self.round_text = f"ROUND {self.current_round} / {TOTAL_ROUNDS}"

        if self.is_break:
            self.bg_color = (0.18, 0.73, 0.35, 1)
            self.timer_color = (1, 1, 1, 1)
            self.status_color = (1, 1, 1, 1)
        else:
            self.bg_color = (1, 1, 1, 1)
            self.status_color = (0.07, 0.07, 0.07, 1)
            if 0 < self.time_left <= 10:
                self.timer_color = (0.90, 0.22, 0.21, 1)
                if not self.ten_sec_played:
                    self.ten_sec_played = True
                    self._play(self.end_sound)
            else:
                self.timer_color = (0.07, 0.07, 0.07, 1)

    def _clear_punch_schedule(self):
        self.round_flash_schedule = set()

    def _can_place_flash(self, second, selected):
        return all(abs(second - existing) >= 2 for existing in selected)

    def _build_round_schedule(self):
        available_until = self.round_duration - 10
        schedule = set()

        minute_start = 0
        while minute_start < available_until:
            minute_end = min(minute_start + 60, available_until)
            minute_range = list(range(minute_start, minute_end))
            random.shuffle(minute_range)
            target_per_minute = min(10, len(minute_range))
            selected_this_minute = []

            for second in minute_range:
                if len(selected_this_minute) >= target_per_minute:
                    break
                if self._can_place_flash(second, schedule):
                    selected_this_minute.append(second)
                    schedule.add(second)

            minute_start += 60

        return schedule

    def _trigger_punch(self):
        if not self.started or self.paused or self.is_break:
            return

        if self.punch_reset_event is not None:
            self.punch_reset_event.cancel()
            self.punch_reset_event = None

        def set_punch_color(_dt):
            self.bg_color = (1.0, 0.92, 0.35, 1)

        def reset_color(_dt):
            self.punch_reset_event = None
            self.bg_color = (0.18, 0.73, 0.35, 1) if self.is_break else (1, 1, 1, 1)

        Clock.schedule_once(set_punch_color, 0)
        self.punch_reset_event = Clock.schedule_once(reset_color, 0.2)
        self._play(self.punch_sound)

    def _setup_phase(self):
        self.ten_sec_played = False
        self._clear_punch_schedule()

        if self.is_break:
            self.status_text = "REST"
            self.time_left = BREAK_SECONDS
        else:
            self.status_text = f"WORK — ROUND {self.current_round}"
            self.round_duration = WORK_SECONDS
            self.time_left = self.round_duration
            self._play(self.start_sound)
            self.round_flash_schedule = self._build_round_schedule()
        self.update_display()

    def _tick(self, _dt):
        if self.paused or not self.started:
            return
        if self.time_left > 0:
            elapsed = self.round_duration - self.time_left
            if not self.is_break and elapsed in self.round_flash_schedule:
                self._trigger_punch()
            self.time_left -= 1
            self.update_display()
        else:
            self.next_step()

    def start_training(self):
        self.started = True
        self.paused = False
        self.current_round = 1
        self.is_break = False
        self._setup_phase()
        if self.timer_event:
            self.timer_event.cancel()
        self.timer_event = Clock.schedule_interval(self._tick, 1)

    def pause_training(self):
        if not self.started:
            return
        self.paused = True
        self.status_text = "PAUSE"

    def resume_training(self):
        if not self.started:
            return
        self.paused = False
        self.status_text = "REST" if self.is_break else f"WORK — ROUND {self.current_round}"

    def stop_training(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self._clear_punch_schedule()
        self.started = False
        self.paused = False
        self.status_text = "STOPPED"

    def reset_training(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self._clear_punch_schedule()
        self.started = False
        self.paused = False
        self.current_round = 1
        self.is_break = False
        self.status_text = "READY"
        self.time_left = WORK_SECONDS
        self.ten_sec_played = False
        self.update_display()

    def next_step(self):
        self._clear_punch_schedule()
        if not self.is_break:
            if self.current_round < TOTAL_ROUNDS:
                self.is_break = True
                self._setup_phase()
            else:
                if self.timer_event:
                    self.timer_event.cancel()
                    self.timer_event = None
                self.started = False
                self.paused = False
                self.status_text = "FINISH!"
                self.round_text = "TRAINING COMPLETE"
                self.time_left = 0
                self.update_display()
        else:
            self.is_break = False
            self.current_round += 1
            self._setup_phase()


class BoxingTimerApp(App):
    def build(self):
        self.title = "Boxing Timer"
        Builder.load_string(KV)
        return TimerScreen()


if __name__ == "__main__":
    BoxingTimerApp().run()
