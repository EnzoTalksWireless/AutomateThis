import time
import pyautogui
import keyboard
import cv2
import numpy as np
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from automation_steps import StepType
import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import QInputDialog, QApplication
def get_application_path():
    """Get the correct application path whether running as script or frozen exe"""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (pyinstaller)
        base_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # If the application is run from a Python interpreter
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Create a user data directory if running as exe
    if getattr(sys, 'frozen', False):
        user_data_dir = os.path.join(os.path.expanduser('~'), 'AutomationTool')
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir
    return base_path

# Directory constants
APPLICATION_PATH = get_application_path()
IMAGES_DIR = os.path.join(APPLICATION_PATH, "images")
AUTOMATIONS_DIR = os.path.join(APPLICATION_PATH, "Saved Automations")
LOGS_DIR = os.path.join(APPLICATION_PATH, "logs")

# Try importing Tesseract, but don't fail if not available
try:
    import pytesseract
    # Check if tesseract binary is actually in the PATH
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except Exception:
        TESSERACT_AVAILABLE = False
except ImportError:
    TESSERACT_AVAILABLE = False

class WorkflowExecutor(QObject):
    """Executes automation workflows"""
    step_started = pyqtSignal(int, str)  # Signal emitted when a step starts
    step_completed = pyqtSignal(int)  # Signal emitted when a step completes
    step_error = pyqtSignal(int, str)  # Signal emitted when a step encounters an error
    workflow_completed = pyqtSignal()  # Signal emitted when the workflow completes
    debug_info = pyqtSignal(str)  # Signal for debug information
    loop_iteration_completed = pyqtSignal(int)  # Signal emitted when a loop iteration completes

    def __init__(self):
        super().__init__()
        self.running = False
        self.paused = False
        self.debug_mode = True  # Enable debug mode by default
        self._execution_log_file = None
        self._execution_log_path = None
        pyautogui.PAUSE = 1.0  # Increase delay for better reliability
        pyautogui.FAILSAFE = True  # Enable fail-safe feature
        
        if TESSERACT_AVAILABLE:
            self._debug_msg("Tesseract OCR is available")
        else:
            self._debug_msg("⚠️ Tesseract OCR binary not found in PATH.")
            self._debug_msg("If you have installed Tesseract, please add its installation folder (e.g., C:\\Program Files\\Tesseract-OCR) to your System PATH environment variable.")
            self._debug_msg("The tool will use OpenCV text detection as a fallback, but Tesseract is highly recommended for better accuracy.")

    def _open_execution_log(self):
        """Create a plain-text log file for this workflow run."""
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._execution_log_path = os.path.join(LOGS_DIR, f"execution_{ts}.log")
            self._execution_log_file = open(
                self._execution_log_path, "w", encoding="utf-8", newline="\n"
            )
            self._execution_log_file.write(
                f"Automation execution log — started {datetime.now().isoformat()}\n"
            )
            self._execution_log_file.write(f"Log file: {self._execution_log_path}\n")
            self._execution_log_file.flush()
        except Exception as e:
            self._execution_log_file = None
            self._execution_log_path = None
            try:
                logging.warning(f"Could not open execution log file: {e}")
            except Exception:
                pass

    def _close_execution_log(self):
        if self._execution_log_file:
            try:
                self._execution_log_file.write(
                    f"\n--- End of execution {datetime.now().isoformat()} ---\n"
                )
                self._execution_log_file.close()
            except Exception:
                pass
            self._execution_log_file = None
        log_path = self._execution_log_path
        self._execution_log_path = None
        if log_path:
            self.debug_info.emit(f"Execution log (plain text): {log_path}")

    def _append_execution_log(self, message):
        """Write a line to the current execution log (no images)."""
        if not self._execution_log_file:
            return
        try:
            # Strip HTML / multi-line for plain text file
            text = message.replace("\r\n", "\n").replace("\r", "\n")
            for line in text.split("\n"):
                self._execution_log_file.write(line + "\n")
            self._execution_log_file.flush()
        except Exception:
            pass

    def execute_workflow(self, steps, loop_count=1):
        """Execute a sequence of automation steps with optional looping"""
        self.running = True
        self.paused = False
        self._open_execution_log()
        _main_iterations = loop_count

        try:
            total_steps = len(steps)
            self._debug_msg(f"\n=== Starting Workflow Execution (Main Loops: {_main_iterations}) ===")
            self._debug_msg(f"Total steps to execute: {total_steps}")
            
            # Reset text input indices for multiple text inputs
            self._reset_text_indices(steps)
            
            # Track which steps have been executed (for non-looping steps)
            executed_non_loop_steps = set()
            
            # Create a structure to track our loop states
            loop_states = {}
            
            # Main workflow loop
            for main_loop in range(_main_iterations):
                if not self.running:
                    self._debug_msg("\n❌ Workflow execution stopped by user")
                    break
                
                self._debug_msg(f"\n=== Starting Main Workflow Iteration {main_loop + 1}/{_main_iterations} ===")
                
                # Reset loop states for each main workflow iteration
                loop_states = {}
                        
                # Start execution from the first step
                i = 0
                while i < len(steps) and self.running:
                    while self.paused:
                        time.sleep(0.1)
                    
                    step = steps[i]
                    step_type = step["type"]
                    params = step["params"]
                    step_name = params.get("name", f"Step {i+1}")
                    
                    # Special handling for loop control steps
                    if step_type == StepType.LOOP_CONTROL:
                        control_type = params.get("control_type")
                        loop_id = params.get("loop_id")
                        
                        if control_type == "start":
                            # Starting a new loop or continuing an existing one
                            if loop_id not in loop_states:
                                # Initialize a new loop
                                nested_loop_count = params.get("loop_count", 1)
                                loop_states[loop_id] = {
                                    "start_index": i,
                                    "iterations_completed": 0,
                                    "loop_count": nested_loop_count
                                }
                                self._debug_msg(f"\n=== Starting Loop {loop_id} (Iterations: {nested_loop_count}) ===")
                            
                            # Check if we've completed all iterations for this loop
                            loop_state = loop_states[loop_id]
                            if loop_state["iterations_completed"] >= loop_state["loop_count"]:
                                # Loop complete, continue to the next step
                                self._debug_msg(f"=== Loop {loop_id} Completed All {loop_state['loop_count']} Iterations ===")
                                i += 1
                                continue
                            
                            # Continue with the next step inside the loop
                            i += 1
                            continue
                            
                        elif control_type == "end":
                            # Check if this is an end for a known loop
                            if loop_id in loop_states:
                                loop_state = loop_states[loop_id]
                                # Increment the iterations counter
                                loop_state["iterations_completed"] += 1
                                self._debug_msg(f"=== Loop {loop_id} Completed Iteration {loop_state['iterations_completed']} ===")
                                
                                # Check if we need to repeat the loop
                                if loop_state["iterations_completed"] < loop_state["loop_count"]:
                                    # Jump back to the start of this loop
                                    i = loop_state["start_index"] + 1  # Skip the start loop step
                                    continue
                                else:
                                    # Loop is complete, continue with the next step
                                    self._debug_msg(f"=== Loop {loop_id} Completed All {loop_state['loop_count']} Iterations ===")
                                    i += 1
                                    continue
                            else:
                                # Error: end of a loop that wasn't started
                                self._debug_msg(f"⚠️ Warning: Found end of loop {loop_id} without a matching start")
                                i += 1
                                continue
                    
                    # Skip non-looping steps that have already been executed in the main workflow loop
                    if not params.get("enable_loop", True) and i in executed_non_loop_steps:
                        self._debug_msg(f"\n=== Skipping non-looping step at step {i+1} ===")
                        i += 1
                        continue
                    
                    # Process regular steps
                    self._debug_msg(f"\n=== Step {i+1}/{total_steps}: {step_name} ({step_type}) ===")
                    self.step_started.emit(i, step_type)
                    
                    try:
                        start_time = time.time()
                        
                        # Execute the step
                        if step_type != StepType.LOOP_CONTROL:  # Skip execution for loop control steps
                            self._execute_step(step_type, params)
                        
                        end_time = time.time()
                        
                        # Mark non-looping steps as executed in the main workflow loop
                        if not params.get("enable_loop", True):
                            executed_non_loop_steps.add(i)
                        
                        self.step_completed.emit(i)
                        execution_time = round(end_time - start_time, 2)
                        self._debug_msg(f"✓ Step {i+1} completed successfully (took {execution_time}s)")
                        
                    except Exception as e:
                        # Convert technical errors to user-friendly messages
                        user_msg = self._get_user_friendly_error(e, step_type)
                        self._debug_msg(f"❌ Error in step {i+1}: {user_msg}")
                        self.step_error.emit(i, user_msg)
                        
                        # Log technical details for debugging
                        self._debug_msg(f"Technical details: {str(e)}")
                        
                        # Continue with next step instead of crashing
                        i += 1
                        continue
                    
                    # Move to the next step
                    i += 1
                
                # Emit main loop iteration completed signal
                if self.running:
                    self.loop_iteration_completed.emit(main_loop + 1)
                    self._debug_msg(f"=== Main Workflow Iteration {main_loop + 1} Completed ===")
            
            self.workflow_completed.emit()
            if self.running:
                self._debug_msg("\n=== Workflow Completed Successfully ===")
            
        finally:
            self.running = False
            self._close_execution_log()

    def _reset_text_indices(self, steps):
        """Reset the current indices for all steps with multiple inputs"""
        for step in steps:
            if step["type"] == StepType.KEYBOARD_TYPE:
                step["params"]["current_text_index"] = 0
            elif step["type"] == StepType.MOUSE_CLICK and step["params"].get("click_type") == "image" and step["params"].get("input_type") == "multiple":
                step["params"]["current_image_index"] = 0

    def _debug_msg(self, message):
        """Log debug message and emit signal with error handling"""
        try:
            logging.debug(message)
        except Exception as e:
            print(f"Logging failed: {str(e)}")
        self._append_execution_log(message)
        self.debug_info.emit(message)

    def _log_error(self, message):
        """Log error message and emit signal with error handling"""
        try:
            logging.error(message)
        except Exception as e:
            print(f"Logging failed: {str(e)}")
        self._append_execution_log(f"❌ {message}")
        self.debug_info.emit(f"❌ {message}")

    def _execute_step(self, step_type, params):
        """Execute a single automation step"""
        if step_type == StepType.MOUSE_CLICK:
            self._execute_mouse_click(params)
        elif step_type == StepType.KEYBOARD_TYPE:
            self._execute_keyboard_type(params)
        elif step_type == StepType.KEYBOARD_SPECIAL:
            self._execute_keyboard_special(params)
        elif step_type == StepType.WAIT:
            self._execute_wait(params)
        elif step_type == StepType.WAIT_FOR_IMAGE:
            self._execute_wait_for_image(params)
        elif step_type == StepType.WAIT_FOR_IMAGE_DISAPPEAR:
            self._execute_wait_for_image(params, disappear=True)
        elif step_type == StepType.LOOP_CONTROL:
            # Loop control steps are handled by the execute_workflow method
            # No direct execution needed here
            pass
        else:
            raise ValueError(f"Unknown step type: {step_type}")

    def _execute_mouse_click(self, step_data):
        """Execute a mouse click step"""
        try:
            click_type = step_data.get("click_type", "coordinates")
            button = step_data.get("button", "left")
            duration = step_data.get("duration", 0.5)
            
            # Get click position
            if click_type == "coordinates":
                x = step_data.get("x", 0)
                y = step_data.get("y", 0)
                pyautogui.moveTo(x, y, duration=duration)
            else:  # image-based click
                confidence = step_data.get("confidence", 0.9)
                if step_data.get("input_type") == "multiple":
                    image_list = step_data.get("image_list") or []
                    if not image_list:
                        raise ValueError("No images in list for multiple image mode")
                    idx = step_data.get("current_image_index", 0)
                    if idx >= len(image_list):
                        idx = 0
                    image_path = image_list[idx]
                    step_data["current_image_index"] = (idx + 1) % len(image_list)
                else:
                    image_path = step_data.get("image_path")

                if not image_path or not os.path.exists(image_path):
                    raise ValueError("Image not found: " + str(image_path))
                
                # Find and click the image
                location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
                if not location:
                    raise ValueError(f"Could not find image on screen: {image_path}")
                
                x, y = location
                pyautogui.moveTo(x, y, duration=duration)
            
            # Perform the click
            pyautogui.click(button=button)
            
            # Handle text input after click if enabled
            if step_data.get("type_after_click"):
                time.sleep(step_data.get("type_delay", 1))
                
                text_to_type = ""
                if step_data.get("text_input_type") == "prompt":
                    # Get the prompt message or use default
                    prompt_message = step_data.get("prompt_message", "Please enter the text:")
                    
                    # Show input dialog and get text
                    text_to_type, ok = QInputDialog.getText(
                        None,  # No parent widget
                        "Input Required",
                        prompt_message,
                        text=step_data.get("text_to_type", "")  # Default text (if any)
                    )
                    
                    if not ok:  # User clicked Cancel
                        raise ValueError("User cancelled text input")
                else:
                    text_to_type = step_data.get("text_to_type", "")
                
                # Type the text
                if text_to_type:
                    pyautogui.write(text_to_type)
                    
                    # Handle special key after typing
                    special_key = step_data.get("special_key")
                    if special_key:
                        pyautogui.press(special_key.lower())
            
            return True
            
        except Exception as e:
            self._log_error(f"Error in mouse click step: {str(e)}")
            raise

    def _execute_keyboard_type(self, params):
        """Execute a keyboard typing action with support for multiple text inputs"""
        if params.get("input_type") == "multiple":
            # Get the current text from the list
            text_list = params.get("text_list", [])
            if not text_list:
                raise ValueError("No text inputs available in multiple input mode")
            
            current_index = params.get("current_text_index", 0)
            if current_index >= len(text_list):
                current_index = 0
            
            # Get the current text to type
            text = text_list[current_index]
            
            # Update the index for the next iteration
            params["current_text_index"] = (current_index + 1) % len(text_list)
        else:
            text = params["text"]

        # UI stores whole seconds (Keyboard Type dialog); interval is per-keystroke delay in seconds
        delay = float(params.get("delay", 1))

        # Type the text using pyautogui.write which handles spaces and special characters better
        self._debug_msg(f"Typing text: {text}")
        pyautogui.write(text, interval=delay)
        
        # Handle special key if specified
        special_key = params.get("special_key")
        if special_key:
            # Convert special key name to pyautogui format
            key_mapping = {
                "Enter": "enter",
                "Tab": "tab",
                "Space": "space",
                "Backspace": "backspace",
                "Delete": "delete",
                "Escape": "esc",
                "Up": "up",
                "Down": "down",
                "Left": "left",
                "Right": "right"
            }
            
            key_to_press = key_mapping.get(special_key, special_key.lower())
            self._debug_msg(f"Pressing special key: {key_to_press}")
            pyautogui.press(key_to_press)
            time.sleep(0.1)  # Small delay after special key

    def _execute_keyboard_special(self, params):
        """Execute a special keyboard action"""
        try:
            key = params["key"].lower()
            modifiers = params.get("modifiers", [])
            
            if key == "windows":
                key = "win"
            
            if key in ["ctrl", "alt", "shift", "win"]:
                modifiers = [mod for mod in modifiers if mod != key]
            
            key_combo = []
            if "ctrl" in modifiers:
                key_combo.append("ctrl")
            if "alt" in modifiers:
                key_combo.append("alt")
            if "shift" in modifiers:
                key_combo.append("shift")
            if key == "win":
                key_combo.insert(0, "win")
            elif "win" in modifiers:
                key_combo.insert(0, "win")
            
            if key != "win":
                key_combo.append(key)
            
            key_sequence = '+'.join(key_combo)
            self._debug_msg(f"Executing keyboard combination: {key_sequence}")
            keyboard.press_and_release(key_sequence)
            time.sleep(0.1)
            
        except Exception as e:
            self._debug_msg(f"Keyboard special action failed: {str(e)}")
            raise

    def _find_image(self, image_path, confidence=0.9):
        """Find an image on screen and return its center coordinates"""
        try:
            # Convert relative path to absolute path if needed
            if not os.path.isabs(image_path):
                image_path = os.path.join(IMAGES_DIR, os.path.basename(image_path))

            if not os.path.exists(image_path):
                raise FileNotFoundError(
                    f"Image file not found: {os.path.basename(image_path)}\n"
                    f"Please make sure the image exists in the 'images' folder."
                )
            
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
            
            # Load and save template image for debugging
            template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                raise RuntimeError(
                    f"Failed to load image: {os.path.basename(image_path)}\n"
                    "Please ensure the image file is a valid image format (PNG, JPG, etc.)"
                )
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            self._debug_msg(f"Best match confidence: {max_val:.4f}")
            
            if max_val >= confidence:
                # Calculate center point
                w, h = template.shape[::-1]
                center_x = max_loc[0] + w//2
                center_y = max_loc[1] + h//2
                self._debug_msg(
                    f"Image match at ({center_x}, {center_y}), confidence {max_val:.4f}"
                )
                return (center_x, center_y)
            
            self._debug_msg(
                f"No match found above confidence threshold ({confidence})\n"
                "Try adjusting the confidence level or updating the reference image."
            )
            return None
            
        except Exception as e:
            self._debug_msg(f"Error finding image: {str(e)}")
            return None

    def _find_text(self, text, region=None, confidence=0.7):
        """Find text on screen using OCR"""
        try:
            # Take screenshot of the specified region or full screen
            screenshot = pyautogui.screenshot(region=region)
            screenshot_np = np.array(screenshot)

            # Try Tesseract first if available
            if TESSERACT_AVAILABLE:
                try:
                    self._debug_msg("Attempting to use Tesseract OCR")
                    result = self._find_text_tesseract(screenshot_np, text, confidence)
                    if result:
                        return result
                except Exception as e:
                    self._debug_msg(f"Tesseract OCR failed: {str(e)}, falling back to OpenCV")

            # Fall back to OpenCV text detection
            self._debug_msg("Using OpenCV text detection")
            return self._find_text_opencv(screenshot_np, text, confidence)

        except Exception as e:
            self._debug_msg(f"Error finding text: {str(e)}")
            return None

    def _find_text_tesseract(self, image_np, target_text, confidence):
        """Find text using Tesseract OCR"""
        # Convert to grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        
        # Apply thresholding to get better OCR results
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Perform OCR
        data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
        
        # Search for target text
        for i, text in enumerate(data['text']):
            if target_text.lower() in text.lower():
                confidence_score = float(data['conf'][i]) / 100
                if confidence_score >= confidence:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    center_x = x + w//2
                    center_y = y + h//2
                    self._debug_msg(f"Tesseract found text with confidence: {confidence_score:.4f}")
                    return (center_x, center_y)
        
        return None

    def _find_text_opencv(self, image_np, target_text, confidence):
        """Find text using OpenCV text detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        
        # Apply preprocessing to improve text detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area and aspect ratio
        text_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(contour)
            
            if 0.1 < aspect_ratio < 10 and area > 100:  # Adjust these thresholds as needed
                text_regions.append((x, y, w, h))
        
        # Sort regions by position (left to right, top to bottom)
        text_regions.sort(key=lambda r: (r[1], r[0]))
        
        # For each region, try to match the text pattern
        for x, y, w, h in text_regions:
            roi = gray[y:y+h, x:x+w]
            
            # Apply additional preprocessing for better matching
            _, roi_binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Calculate similarity with target text pattern
            # This is a simplified approach - in practice, you might want to use
            # more sophisticated pattern matching or feature extraction
            similarity = self._calculate_text_similarity(roi_binary, target_text)
            
            if similarity >= confidence:
                center_x = x + w//2
                center_y = y + h//2
                self._debug_msg(f"OpenCV found potential text match with confidence: {similarity:.4f}")
                return (center_x, center_y)
        
        return None

    def _calculate_text_similarity(self, roi, target_text):
        """Calculate similarity between ROI and target text pattern"""
        # This is a simplified implementation
        # You might want to implement more sophisticated text recognition here
        # For now, we'll use basic image statistics as a rough approximation
        
        # Normalize ROI
        roi_norm = cv2.normalize(roi, None, 0, 1, cv2.NORM_MINMAX)
        
        # Calculate basic statistics
        mean = np.mean(roi_norm)
        std = np.std(roi_norm)
        
        # Return a confidence score based on image statistics
        # This is a very basic approach and should be improved based on your needs
        return (mean + std) / 2

    def _get_user_friendly_error(self, error, step_type):
        """Convert technical error messages to user-friendly ones"""
        error_str = str(error).lower()
        
        if "image not found" in error_str:
            return "Could not find the reference image file. Please make sure the image exists and try again."
        elif "confidence" in error_str:
            return "The confidence threshold must be between 0.1 and 1.0. Please adjust it and try again."
        elif "timeout" in error_str:
            return "The operation timed out. Please check if the target is visible on screen or adjust the timeout value."
        else:
            return str(error)

    def pause(self):
        """Pause workflow execution"""
        self.paused = True

    def resume(self):
        """Resume workflow execution"""
        self.paused = False

    def stop(self):
        """Stop workflow execution"""
        self.running = False

    def _execute_wait(self, params):
        """Execute a wait step"""
        duration = params.get("duration", 1)
        self._debug_msg(f"Waiting for {duration} seconds")
        time.sleep(duration)

    def _validate_reference_image_path(self, image_path):
        """Resolve reference image to an existing file path (absolute or under images folder)."""
        if not image_path or not str(image_path).strip():
            raise ValueError("No reference image path specified")
        p = os.path.abspath(os.path.expanduser(image_path.strip()))
        if os.path.isfile(p):
            return p
        alt = os.path.join(IMAGES_DIR, os.path.basename(p))
        if os.path.isfile(alt):
            return alt
        raise ValueError("Image not found: " + str(image_path))

    def _execute_wait_for_image(self, params, disappear=False):
        """Poll the screen until reference image appears (or disappears)."""
        image_path = self._validate_reference_image_path(params.get("image_path", ""))
        confidence = float(params.get("confidence", 0.9))
        timeout_sec = max(1, int(params.get("timeout", 30)))
        deadline = time.time() + timeout_sec
        interval = 0.25

        goal = "leave the screen" if disappear else "appear"
        self._debug_msg(
            f"Waiting for image to {goal} (timeout {timeout_sec}s, confidence {confidence:.2f})"
        )

        while self.running and time.time() < deadline:
            while self.paused and self.running:
                time.sleep(0.1)
            found = self._find_image(image_path, confidence=confidence)
            if disappear:
                if found is None:
                    self._debug_msg("Reference image no longer matched on screen")
                    return
            else:
                if found is not None:
                    self._debug_msg("Reference image matched on screen")
                    return
            time.sleep(interval)

        if not self.running:
            raise ValueError("Workflow stopped while waiting for image")

        action = "disappear" if disappear else "appear"
        raise ValueError(
            f"Timeout: reference image did not {action} within {timeout_sec} seconds"
        )
