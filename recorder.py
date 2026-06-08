import threading
import time
import pyautogui
import keyboard
import mouse
from PyQt6.QtCore import QObject, pyqtSignal
from automation_steps import StepType

class ActionRecorder(QObject):
    """Records user actions for automation"""
    action_recorded = pyqtSignal(str, dict)  # Signal emitted when an action is recorded
    recording_stopped = pyqtSignal()  # Signal emitted when recording stops
    coordinate_recorded = pyqtSignal(int, int)  # Signal emitted when coordinates are recorded
    recording_armed = pyqtSignal(bool)  # Signal emitted when recording is armed/disarmed

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.is_coordinate_recording = False
        self.is_coordinate_armed = False
        self.record_thread = None
        self.last_mouse_pos = None
        self.last_click_time = 0
        self.key_buffer = []
        self.key_buffer_time = 0
        self.keyboard_hook_handler = None
        self.mouse_hook_handler = None
        self.coordinate_hotkey_handler = None
        # Keys currently held (excludes OS typematic repeat KEY_DOWNs)
        self._keys_physically_down = set()

    @staticmethod
    def _is_modifier_key(name):
        """True if this key is a modifier (never emit alone; used in combos)."""
        if not name:
            return False
        n = name.lower()
        return n in (
            "ctrl", "left ctrl", "right ctrl",
            "alt", "left alt", "right alt",
            "shift", "left shift", "right shift",
            "windows", "win", "left windows", "right windows",
        )

    def _active_modifiers(self):
        """Which modifier toggles are held (order matches Keyboard Special UI)."""
        mods = []
        if keyboard.is_pressed("ctrl"):
            mods.append("ctrl")
        if keyboard.is_pressed("alt"):
            mods.append("alt")
        if keyboard.is_pressed("shift"):
            mods.append("shift")
        if keyboard.is_pressed("windows") or keyboard.is_pressed("win"):
            mods.append("win")
        return mods

    @staticmethod
    def _event_name_to_dialog_key(name):
        """Map keyboard hook name to Keyboard Special dialog key text."""
        if not name:
            return ""
        n = name.lower()
        special = {
            "enter": "Enter",
            "tab": "Tab",
            "space": "Space",
            "backspace": "Backspace",
            "delete": "Delete",
            "esc": "Escape",
            "escape": "Escape",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
        }
        if n in special:
            return special[n]
        if n.startswith("f") and len(n) <= 3 and n[1:].isdigit():
            return "F" + n[1:]
        if len(name) == 1:
            if name.isalpha():
                return name.upper()
            return name
        return name

    def _format_combo_name(self, key, modifiers):
        labels = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Windows"}
        parts = [labels[m] for m in modifiers if m in labels]
        parts.append(key)
        return " + ".join(parts)

    def _emit_keyboard_special(self, key, modifiers, name=None):
        """Emit a step compatible with KeyboardSpecialDialog and executor (key + modifiers)."""
        self._flush_key_buffer()
        display = name or self._format_combo_name(key, modifiers)
        self.action_recorded.emit(StepType.KEYBOARD_SPECIAL, {
            "name": display,
            "key": key,
            "modifiers": list(modifiers),
        })

    def start_recording(self):
        """Start recording user actions"""
        if not self.is_recording:
            self._keys_physically_down.clear()
            self.is_recording = True
            self.record_thread = threading.Thread(target=self._record_loop)
            self.record_thread.daemon = True
            self.record_thread.start()

    def stop_recording(self):
        """Stop recording user actions"""
        self.is_recording = False
        if self.record_thread:
            self.record_thread.join()
        self._keys_physically_down.clear()
        self.recording_stopped.emit()

    def start_coordinate_recording(self):
        """Arm the coordinate recording"""
        if not self.is_coordinate_armed:
            self.is_coordinate_armed = True
            self.coordinate_hotkey_handler = keyboard.on_press(
                lambda e: self._start_actual_recording(e)
                if e.name == 'f8' and keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift')
                else None
            )
            self.recording_armed.emit(True)

    def stop_coordinate_recording(self):
        """Stop recording coordinates"""
        if self.is_coordinate_armed or self.is_coordinate_recording:
            self.is_coordinate_armed = False
            self.is_coordinate_recording = False
            if self.coordinate_hotkey_handler:
                try:
                    keyboard.unhook(self.coordinate_hotkey_handler)
                except Exception:
                    pass
                self.coordinate_hotkey_handler = None
            self.recording_armed.emit(False)

    def _start_actual_recording(self, event):
        """Start the actual coordinate recording when Ctrl+Shift+F8 is pressed"""
        if self.is_coordinate_armed:
            self.stop_coordinate_recording()
            # Get current mouse position
            x, y = pyautogui.position()
            self.coordinate_recorded.emit(x, y)

    def _record_loop(self):
        """Main recording loop"""
        # Initialize listeners
        self.keyboard_hook_handler = keyboard.hook(self._on_keyboard_event)
        self.mouse_hook_handler = mouse.hook(self._on_mouse_event)

        while self.is_recording:
            # Process any buffered keyboard input
            current_time = time.time()
            if self.key_buffer and (current_time - self.key_buffer_time) > 1.0:
                self._flush_key_buffer()
            time.sleep(0.01)

        # Clean up
        if self.keyboard_hook_handler:
            try:
                keyboard.unhook(self.keyboard_hook_handler)
            except Exception:
                pass
            self.keyboard_hook_handler = None
        if self.mouse_hook_handler:
            try:
                mouse.unhook(self.mouse_hook_handler)
            except Exception:
                pass
            self.mouse_hook_handler = None

    def _on_keyboard_event(self, event):
        """Handle keyboard events"""
        if not self.is_recording:
            return

        name = getattr(event, "name", None) or ""

        # Track key-up so we only react once per physical press (ignore typematic repeat)
        if event.event_type == keyboard.KEY_UP:
            self._keys_physically_down.discard(name)
            return

        if event.event_type != keyboard.KEY_DOWN:
            return

        if name in self._keys_physically_down:
            return
        self._keys_physically_down.add(name)

        # Modifiers never create their own step; they combine with the next key (e.g. Alt+Tab).
        if self._is_modifier_key(name):
            return

        mods = self._active_modifiers()
        has_chord = bool(mods)
        shift_only = mods == ["shift"]
        has_ctrl_alt_win = any(m in mods for m in ("ctrl", "alt", "win"))

        dialog_key = self._event_name_to_dialog_key(name)
        nlow = name.lower()

        # Shift + letter: typing uppercase, not a separate "Shift" step
        if (
            shift_only
            and not has_ctrl_alt_win
            and len(name) == 1
            and name.isalpha()
        ):
            self.key_buffer.append(name.upper())
            self.key_buffer_time = time.time()
            return

        # No modifiers: typing vs single-key specials (Tab, Enter, F-keys, arrows, etc.)
        if not has_chord:
            standalone_special = (
                "enter",
                "tab",
                "backspace",
                "delete",
                "esc",
                "escape",
                "up",
                "down",
                "left",
                "right",
            )
            if nlow in standalone_special or (
                nlow.startswith("f") and len(nlow) <= 3 and nlow[1:].isdigit()
            ):
                self._emit_keyboard_special(dialog_key, [])
                return
            if name == "space":
                self.key_buffer.append(" ")
                self.key_buffer_time = time.time()
                return
            if len(name) == 1 and name.isprintable():
                self.key_buffer.append(name)
                self.key_buffer_time = time.time()
                return
            return

        # Modifier chord: one Keyboard Special step (Alt+Tab, Ctrl+C, Shift+Tab, …)
        self._emit_keyboard_special(dialog_key, mods)

    def _on_mouse_event(self, event):
        """Handle mouse events"""
        if not self.is_recording:
            return

        current_time = time.time()
        
        # Handle clicks
        if (
            hasattr(event, 'button')
            and event.button in [mouse.LEFT, mouse.RIGHT]
            and getattr(event, 'event_type', None) == 'down'
        ):
            # Avoid duplicate events
            if current_time - self.last_click_time < 0.1:
                return
                
            self.last_click_time = current_time
            # Get current mouse position using pyautogui
            x, y = pyautogui.position()
            
            # Flush any pending keyboard input
            self._flush_key_buffer()
            
            self.action_recorded.emit(StepType.MOUSE_CLICK, {
                "name": f"Click at ({x}, {y})",
                "click_type": "coordinates",
                "x": x,
                "y": y
            })

    def _flush_key_buffer(self):
        """Flush the keyboard buffer as a typing action"""
        if self.key_buffer:
            text = ''.join(self.key_buffer)
            self.action_recorded.emit(StepType.KEYBOARD_TYPE, {
                "name": f"Type '{text}'",
                "text": text,
                "delay": 10  # Default delay between keystrokes
            })
            self.key_buffer = []

    def take_screenshot(self, x, y, width, height):
        """Take a screenshot of a specific region"""
        try:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            return screenshot
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None 