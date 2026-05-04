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

ROUND_SIGNAL_CONFIG = {
    3: {"repeats": 3, "control": (6.0, 10.0), "attack": (2.0, 3.0)},
    4: {"repeats": 4, "control": (5.0, 9.0), "attack": (2.0, 2.5)},
    5: {"repeats": 5, "control": (4.0, 8.0), "attack": (1.8, 2.5)},
    6: {"repeats": 6, "control": (4.0, 7.0), "attack": (1.5, 2.2)},
    7: {"repeats": 7, "control": (3.0, 6.0), "attack": (1.2, 2.0)},
    8: {"repeats": 8, "control": (3.0, 5.0), "attack": (1.0, 1.8)},
}

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
    finished = BooleanProperty(False)

    status_text = StringProperty("READY")
    round_text = StringProperty(f"ROUND 1 / {TOTAL_ROUNDS}")
    timer_text = StringProperty("03:00")

    bg_color = ListProperty([1, 1, 1, 1])
    timer_color = ListProperty([0.07, 0.07, 0.07, 1])
    status_color = ListProperty([0.07, 0.07, 0.07, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timer_event = None
        self.round_duration = WORK_SECONDS
        self.ten_sec_played = False
        self.start_sound = self._load_sound("start.mp3")
        self.end_sound = self._load_sound("end10.mp3")
        self.punch_sound = self._load_sound("punch.mp3")
        self.attack_sound = self._load_sound("atack.mp3")

        self.phase_plan = []
        self.phase_by_second = {}
        self.signal_schedule = []
        self.last_signal_second = None

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

    def _is_phase_round(self):
        return self.current_round >= 3 and not self.is_break

    def _current_phase(self):
        if not self._is_phase_round():
            return None
        elapsed = self.round_duration - self.time_left
        return self.phase_by_second.get(elapsed)

    def update_display(self):
        self.timer_text = self._format_time(self.time_left)
        if self.finished:
            self.status_text = "end"
            self.round_text = f"ROUND {TOTAL_ROUNDS} / {TOTAL_ROUNDS}"
            self.bg_color = (0.80, 1.0, 0.56, 1)
            self.timer_color = (0.07, 0.07, 0.07, 1)
            self.status_color = (0.07, 0.07, 0.07, 1)
            return

        self.round_text = f"ROUND {self.current_round} / {TOTAL_ROUNDS}"

        if self.is_break:
            self.bg_color = (0.18, 0.73, 0.35, 1)
            self.timer_color = (1, 1, 1, 1)
            self.status_color = (1, 1, 1, 1)
        else:
            phase = self._current_phase()
            if self.current_round <= 2:
                self.bg_color = (0.55, 0.55, 0.55, 1)
            elif phase == "attack":
                self.bg_color = (0.92, 0.16, 0.14, 1)
            else:
                self.bg_color = (0.23, 0.56, 0.32, 1)

            self.status_color = (1, 1, 1, 1)
            self.timer_color = (1, 1, 1, 1)
            if 0 < self.time_left <= 10 and not self.ten_sec_played:
                self.ten_sec_played = True
                self._play(self.end_sound)

    def _clear_round_state(self):
        self.signal_schedule = []
        self.phase_plan = []
        self.phase_by_second = {}
        self.last_signal_second = None

    def _generate_phase_plan(self):
        config = ROUND_SIGNAL_CONFIG[self.current_round]
        phases = ["control", "attack"] * config["repeats"]
        random.shuffle(phases)

        remaining = self.round_duration
        plan = []
        for idx, phase in enumerate(phases):
            lo, hi = (10, 20) if phase == "control" else (5, 10)
            duration = int(random.uniform(lo, hi))
            min_for_rest = max(0, len(phases) - idx - 1)
            duration = min(duration, max(1, remaining - min_for_rest))
            plan.append({"phase": phase, "duration": duration})
            remaining -= duration
            if remaining <= 0:
                break

        if remaining > 0 and plan:
            plan[-1]["duration"] += remaining

        second = 0
        phase_by_second = {}
        for item in plan:
            phase_name = item["phase"]
            for _ in range(item["duration"]):
                phase_by_second[second] = "control" if phase_name == "control" else "attack"
                second += 1
        return plan, phase_by_second

    def _schedule_signals(self):
        if self.current_round <= 2:
            self.signal_schedule = []
            return

        config = ROUND_SIGNAL_CONFIG[self.current_round]
        schedule = []
        t = 0.0
        while t < self.round_duration - 3:
            phase = self.phase_by_second.get(int(t), "control")
            interval_min, interval_max = config[phase]
            interval = random.uniform(interval_min, interval_max)
            t += interval

            if phase == "attack" and random.random() < 0.28:
                t += random.uniform(2.0, 4.0)

            second = int(t)
            if second >= self.round_duration - 1:
                break
            if schedule and abs(second - schedule[-1]) < 2:
                continue
            schedule.append(second)

            if phase == "attack" and random.random() < 0.3:
                follow_up = second + random.randint(1, 2)
                if follow_up < self.round_duration - 1:
                    schedule.append(follow_up)

        self.signal_schedule = sorted(set(schedule))

    def _trigger_signal(self, second):
        phase = self.phase_by_second.get(second, "control")
        self.last_signal_second = second
        if phase == "attack":
            if random.random() < 0.5:
                self.status_text = "АТАКА: джеб → оттяжка → серия двоек (2–4) → выход"
            else:
                self.status_text = "АТАКА БЛИЦ: джеб → оттяжка → 2 быстрые двойки → выход"
            self._play(self.attack_sound or self.punch_sound)
        else:
            self.status_text = "КОНТРОЛЬ: джеб → оттяжка → двойка → выход"
            self._play(self.punch_sound)

    def _setup_phase(self):
        self.ten_sec_played = False
        self._clear_round_state()

        if self.is_break:
            self.status_text = "REST"
            self.time_left = BREAK_SECONDS
            self.round_duration = BREAK_SECONDS
        else:
            self.round_duration = WORK_SECONDS
            self.time_left = self.round_duration
            if self.current_round <= 2:
                self.status_text = f"РАЗМИНКА — ROUND {self.current_round}"
            else:
                self.status_text = f"WORK — ROUND {self.current_round}"
                self.phase_plan, self.phase_by_second = self._generate_phase_plan()
                self._schedule_signals()
            self._play(self.start_sound)
        self.update_display()

    def _tick(self, _dt):
        if self.paused or not self.started:
            return
        if self.time_left > 0:
            elapsed = self.round_duration - self.time_left
            if not self.is_break and elapsed in self.signal_schedule:
                self._trigger_signal(elapsed)
            elif not self.is_break and self.current_round >= 3:
                second = elapsed
                self.status_text = "Без сигнала: движение, джеб, контроль дистанции"
                if self.last_signal_second is not None and second - self.last_signal_second > 6:
                    self.status_text = "ТИШИНА: работай первым (джеб, вход)"
            self.time_left -= 1
            self.update_display()
        else:
            self.next_step()

    def start_training(self):
        self.started = True
        self.paused = False
        self.finished = False
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
        if self.is_break:
            self.status_text = "REST"
        elif self.current_round <= 2:
            self.status_text = f"РАЗМИНКА — ROUND {self.current_round}"
        else:
            self.status_text = f"WORK — ROUND {self.current_round}"

    def stop_training(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self._clear_round_state()
        self.started = False
        self.paused = False
        self.status_text = "STOPPED"

    def reset_training(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        self._clear_round_state()
        self.started = False
        self.paused = False
        self.finished = False
        self.current_round = 1
        self.is_break = False
        self.status_text = "READY"
        self.time_left = WORK_SECONDS
        self.round_duration = WORK_SECONDS
        self.ten_sec_played = False
        self.update_display()

    def next_step(self):
        self._clear_round_state()
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
                self.finished = True
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

    def on_start(self):
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            LayoutParams = autoclass("android.view.WindowManager$LayoutParams")

            @run_on_ui_thread
            def keep_screen_on():
                activity = PythonActivity.mActivity
                activity.getWindow().addFlags(LayoutParams.FLAG_KEEP_SCREEN_ON)

            keep_screen_on()
        except Exception:
            pass


if __name__ == "__main__":
    BoxingTimerApp().run()
