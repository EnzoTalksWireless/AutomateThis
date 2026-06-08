import sys
import logging
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QListWidget, QTabWidget, QSpinBox, QCheckBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QDialog, QListWidgetItem,
    QProgressDialog, QGroupBox, QTextEdit, QStyle, QStyleFactory
)
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal, QThread, QMetaObject
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPalette, QColor, QFont, QShortcut, QKeySequence
import os
import time
import copy
import keyboard

from automation_steps import StepType, STEP_DIALOGS
from recorder import ActionRecorder
from executor import WorkflowExecutor, LOGS_DIR

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
WORKSPACE_DIR = get_application_path()
IMAGES_DIR = os.path.join(WORKSPACE_DIR, "images")
AUTOMATIONS_DIR = os.path.join(WORKSPACE_DIR, "Saved Automations")
DEBUG_DIR = os.path.join(WORKSPACE_DIR, "debug")

# Ensure directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(AUTOMATIONS_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging - this will be used by all modules
try:
    # Remove any existing handlers to prevent duplicate logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    # Configure new handlers
    log_file = os.path.join(DEBUG_DIR, 'automation.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    console_handler = logging.StreamHandler()
    
    # Set formatter for both handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(file_handler)
    logging.root.addHandler(console_handler)
    
except Exception as e:
    # If file logging fails, configure console-only logging
    print(f"Warning: Could not set up file logging. Using console only. Error: {str(e)}")
    
    # Remove any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure console-only logging
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(console_handler)

# Modern UI Style Sheet
STYLE_SHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: system;
    font-size: 10pt;
}

QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 70px;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #3d3d3d;
    border: 1px solid #4d4d4d;
}

QPushButton:pressed {
    background-color: #4d4d4d;
}

/* Style for emoji characters in buttons */
QPushButton[text*="⏺️"], QPushButton[text*="▶️"], QPushButton[text*="⏸️"], 
QPushButton[text*="⏯️"], QPushButton[text*="⏹️"], QPushButton[text*="✏️"], 
QPushButton[text*="🗑️"], QPushButton[text*="➕"], QPushButton[text*="🔍"], 
QPushButton[text*="📋"], QPushButton[text*="🧹"], QPushButton[text*="📁"],
QPushButton[text*="✅"], QPushButton[text*="❌"] {
    font-size: 10pt;
    padding-top: 4px;
    padding-bottom: 4px;
}

/* Style specific to automation steps in the list */
QListWidget::item {
    min-height: 35px;  /* Reduced height for each step in the list */
    font-size: 9pt;    /* Smaller font size */
    padding: 2px;      /* Reduced padding */
}

QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 2px 4px;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #0078D4;
}

QListWidget {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #0078D4;
    color: white;
}

QListWidget::item:hover {
    background-color: #3d3d3d;
}

QTabWidget::pane {
    border: 1px solid #3d3d3d;
    background-color: #1e1e1e;
}

QTabWidget::tab-bar {
    left: 5px;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-bottom: none;
    padding: 5px 10px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #3d3d3d;
    border-bottom: none;
}

QTabBar::tab:hover {
    background-color: #4d4d4d;
}

QGroupBox {
    margin-top: 12px;
    padding-top: 16px;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}

QGroupBox::title {
    color: #e0e0e0;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}

QTextEdit {
    font-family: 'Consolas', 'Courier New', monospace;
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QScrollBar:vertical {
    border: none;
    background-color: #2d2d2d;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #4d4d4d;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #5d5d5d;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #2d2d2d;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #4d4d4d;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #5d5d5d;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Removing checkbox styling to use default */
/* QCheckBox {
    color: #e0e0e0;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #3d3d3d;
    border-radius: 3px;
    background-color: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #0078D4;
}

QCheckBox::indicator:hover {
    border: 1px solid #4d4d4d;
} */

QMenuBar {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border-bottom: 1px solid #3d3d3d;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}

QMenuBar::item:selected {
    background-color: #3d3d3d;
}

QMenu {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
}

QMenu::item {
    padding: 4px 20px;
}

QMenu::item:selected {
    background-color: #3d3d3d;
}

QStatusBar {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border-top: 1px solid #3d3d3d;
}

/* Make the window more compact */
QMainWindow {
    min-width: 800px;
    min-height: 600px;
}

/* Adjust layout spacing */
QVBoxLayout, QHBoxLayout {
    spacing: 4px;
    margin: 2px;
}
"""

class StepsListWidget(QListWidget):
    """List widget that notifies before an internal drag-drop reorder (for undo)."""
    beforeReorder = pyqtSignal()

    def dropEvent(self, event):
        self.beforeReorder.emit()
        super().dropEvent(event)


class AutomationStep(QFrame):
    """Represents a single automation step in the workflow"""
    stepMoved = pyqtSignal(int, int)  # Signal for drag and drop reordering
    paramsChanged = pyqtSignal(dict)  # Signal for parameter updates
    copyRequested = pyqtSignal(object)  # Signal for copy request
    beforeDelete = pyqtSignal()  # Emitted before this step is removed (undo snapshot)
    beforeEditCommit = pyqtSignal()  # Emitted before edited params are applied (undo snapshot)

    def __init__(self, step_type, params=None, parent=None):
        super().__init__(parent)
        self.step_type = step_type
        self.params = params or {}
        self.setup_ui()
        self.paramsChanged.connect(self._update_ui)

    def setup_ui(self):
        # Clear any existing layout
        if self.layout():
            QWidget().setLayout(self.layout())
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        
        # Set minimum height for the step - reduced for smaller text
        self.setMinimumHeight(40)
        
        # Set styling for the step frame
        base_style = """
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 9pt;
            }
            QPushButton {
                font-size: 9pt;
                padding: 3px 6px;
                min-height: 22px;
            }
        """
        
        # Special styling for loop control steps
        if self.step_type == StepType.LOOP_CONTROL:
            if self.params.get("control_type") == "start":
                # Start loop gets a green background
                self.setStyleSheet(base_style + """
                    QFrame {
                        background-color: #1e3b2d;
                        border: 1px solid #2e5b3d;
                    }
                """)
            else:
                # End loop gets a rust background
                self.setStyleSheet(base_style + """
                    QFrame {
                        background-color: #3b2d1e;
                        border: 1px solid #5b3d2e;
                    }
                """)
        else:
            # Regular steps
            self.setStyleSheet(base_style)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)  # Reduced padding
        layout.setSpacing(6)  # Reduced spacing
        self.setLayout(layout)
        
        # Step type label with distinct color
        self.type_label = QLabel(self.step_type)
        self.type_label.setStyleSheet("color: #88CCFF; font-weight: bold; font-size: 9pt;")
        layout.addWidget(self.type_label)

        # Step name label
        self.name_label = QLabel(self.params.get("name", ""))
        layout.addWidget(self.name_label)

        # Coordinates label (for mouse click steps)
        if self.step_type == StepType.MOUSE_CLICK:
            coords = f"({self.params.get('x', '?')}, {self.params.get('y', '?')})"
            self.coord_label = QLabel(coords)
            self.coord_label.setStyleSheet("color: #FFCC88; font-size: 9pt;")  # Distinct color for coordinates
            layout.addWidget(self.coord_label)
        
        # Special info for loop control steps
        elif self.step_type == StepType.LOOP_CONTROL:
            loop_id = self.params.get("loop_id", 1)
            control_type = self.params.get("control_type", "start")
            
            if control_type == "start":
                loop_count = self.params.get("loop_count", 1)
                loop_info = f"Loop #{loop_id} - {loop_count} iterations"
                self.loop_label = QLabel(loop_info)
                self.loop_label.setStyleSheet("color: #AAFFAA; font-size: 9pt;")
            else:
                loop_info = f"End Loop #{loop_id}"
                self.loop_label = QLabel(loop_info)
                self.loop_label.setStyleSheet("color: #FFCC88; font-size: 9pt;")
                
            layout.addWidget(self.loop_label)

        elif self.step_type in (
            StepType.WAIT_FOR_IMAGE,
            StepType.WAIT_FOR_IMAGE_DISAPPEAR,
        ):
            ip = (self.params.get("image_path") or "").strip()
            short = os.path.basename(ip) if ip else "—"
            to = self.params.get("timeout", 30)
            pct = int(round(float(self.params.get("confidence", 0.9)) * 100))
            suffix = "until gone" if self.step_type == StepType.WAIT_FOR_IMAGE_DISAPPEAR else "until visible"
            self.wait_image_label = QLabel(f"{short} · {pct}% · {to}s {suffix}")
            self.wait_image_label.setStyleSheet("color: #C9A0DC; font-size: 9pt;")
            layout.addWidget(self.wait_image_label)

        # Add spacer to push buttons to the right
        layout.addStretch(1)

        # Copy button with enhanced emoji
        copy_btn = QPushButton("📋 Copy")
        copy_btn.clicked.connect(self.copy_step)
        copy_btn.setStyleSheet("""
            QPushButton {
                color: #e0e0e0;
                background-color: #3a3a3a;
                border: 1px solid #4d4d4d;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        layout.addWidget(copy_btn)

        # Edit button with enhanced emoji
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(self.edit_step)
        edit_btn.setStyleSheet("""
            QPushButton {
                color: #e0e0e0;
                background-color: #3a3a3a;
                border: 1px solid #4d4d4d;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        layout.addWidget(edit_btn)

        # Delete button with enhanced emoji
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_step)
        delete_btn.setStyleSheet("""
            QPushButton {
                color: #e0e0e0;
                background-color: #3a3a3a;
                border: 1px solid #4d4d4d;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                color: #ff8888;
            }
        """)
        layout.addWidget(delete_btn)

    def _update_ui(self):
        """Update UI elements with current parameters"""
        # Ensure we're on the main thread
        if not self.thread() == QApplication.instance().thread():
            # Schedule update for main thread
            QMetaObject.invokeMethod(self, "_update_ui", Qt.ConnectionType.QueuedConnection)
            return
            
        # Update step name
        self.name_label.setText(self.params.get("name", ""))
        
        # Update coordinates for mouse clicks
        if self.step_type == StepType.MOUSE_CLICK and hasattr(self, "coord_label"):
            coords = f"({self.params.get('x', '?')}, {self.params.get('y', '?')})"
            self.coord_label.setText(coords)
        
        # Update loop control info
        elif self.step_type == StepType.LOOP_CONTROL and hasattr(self, "loop_label"):
            loop_id = self.params.get("loop_id", 1)
            control_type = self.params.get("control_type", "start")
            
            if control_type == "start":
                loop_count = self.params.get("loop_count", 1)
                loop_info = f"Loop #{loop_id} - {loop_count} iterations"
                self.loop_label.setText(loop_info)
            else:
                loop_info = f"End Loop #{loop_id}"
                self.loop_label.setText(loop_info)

        elif self.step_type in (
            StepType.WAIT_FOR_IMAGE,
            StepType.WAIT_FOR_IMAGE_DISAPPEAR,
        ) and hasattr(self, "wait_image_label"):
            ip = (self.params.get("image_path") or "").strip()
            short = os.path.basename(ip) if ip else "—"
            to = self.params.get("timeout", 30)
            pct = int(round(float(self.params.get("confidence", 0.9)) * 100))
            suffix = "until gone" if self.step_type == StepType.WAIT_FOR_IMAGE_DISAPPEAR else "until visible"
            self.wait_image_label.setText(f"{short} · {pct}% · {to}s {suffix}")
                
        # Re-apply styling based on step type and parameters
        self.setup_ui()

    def update_params(self, new_params):
        """Thread-safe method to update parameters"""
        self.params.update(new_params)
        # Emit signal to trigger UI update in main thread
        self.paramsChanged.emit(self.params.copy())

    def edit_step(self):
        if self.step_type in STEP_DIALOGS:
            # Pass the current parameters to the dialog
            dialog = STEP_DIALOGS[self.step_type](params=self.params.copy())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.beforeEditCommit.emit()
                self.update_params(dialog.get_params())

    def delete_step(self):
        """Delete this step from the list"""
        self.beforeDelete.emit()
        # Find the QListWidgetItem that contains this widget
        list_widget = self.parent().parent()  # Get the QListWidget
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if list_widget.itemWidget(item) == self:
                # Remove both the widget and the item
                list_widget.takeItem(i)
                self.deleteLater()
                break

    def get_data(self):
        """Get step data for saving"""
        return {
            "type": self.step_type,
            "params": self.params
        }

    def copy_step(self):
        """Signal that this step should be copied"""
        self.copyRequested.emit(self)

class AddStepDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Automation Step")
        self.setModal(True)
        self.selected_type = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Set dialog styling for dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 10pt;
            }
            QLabel[text^="🔍"] {
                font-size: 11pt;
                color: #88CCFF;
            }
            QPushButton {
                background-color: #424242;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4e4e4e;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
            QPushButton[text^="✅"] {
                background-color: #2a5d3c;
            }
            QPushButton[text^="✅"]:hover {
                background-color: #336d49;
            }
            QPushButton[text^="❌"] {
                background-color: #5d2a2a;
            }
            QPushButton[text^="❌"]:hover {
                background-color: #6d3333;
            }
            QComboBox {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #555555;
                border-left-style: solid;
            }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d;
                color: #e0e0e0;
                selection-background-color: #4e4e4e;
            }
        """)

        # Step type selection
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            StepType.MOUSE_CLICK,
            StepType.KEYBOARD_TYPE,
            StepType.KEYBOARD_SPECIAL,
            StepType.WAIT,
            StepType.WAIT_FOR_IMAGE,
            StepType.WAIT_FOR_IMAGE_DISAPPEAR,
            StepType.LOOP_CONTROL
        ])
        
        # Create label with enhanced emoji
        step_type_label = QLabel("🔍 Step Type:")
        step_type_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #88CCFF;")
        
        layout.addWidget(step_type_label)
        layout.addWidget(self.type_combo)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("✅ OK")
        cancel_btn = QPushButton("❌ Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def get_selected_type(self):
        return self.type_combo.currentText()

class ExecutorThread(QThread):
    """Thread for executing automation workflows"""
    def __init__(self, executor, steps):
        super().__init__()
        self.executor = executor
        self.steps = steps
        self.loop_count = 1  # Default to 1 loop

    def start(self, loop_count=1):
        """Start the thread with specified loop count"""
        self.loop_count = loop_count
        super().start()

    def run(self):
        """Execute the workflow in a separate thread"""
        self.executor.execute_workflow(self.steps, self.loop_count)

class AutomationToolGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Automation Tool")
        self.setMinimumSize(800, 600)  # Reduced window size
        self.setWindowState(Qt.WindowState.WindowMaximized)  # Start maximized
        
        # Set application icon
        icon_path = os.path.join(WORKSPACE_DIR, "icon.ico")
        fallback_icon_path = os.path.join(WORKSPACE_DIR, "icon.png")
        
        app_icon = QIcon()
        if os.path.exists(icon_path):
            app_icon.addFile(icon_path)
        elif os.path.exists(fallback_icon_path):
            app_icon.addFile(fallback_icon_path)
        
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
            # Set taskbar icon
            if hasattr(sys, 'getwindowsversion'):  # Windows only
                import ctypes
                myappid = 'mycompany.erpautomation.1.0'  # Arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        # Set modern style
        self.setStyleSheet(STYLE_SHEET)
        
        # Initialize components
        self.recorder = ActionRecorder()
        self.executor = WorkflowExecutor()
        self.executor_thread = None
        self.current_workflow_path = None
        self.coordinate_recording = False
        self.progress_dialog = None  # Initialize as None
        self.copied_steps = []  # Store copied steps
        self.record_stop_hotkey = None
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo_steps = 50
        self._undo_in_progress = False
        
        # Setup fail-safe shortcut
        keyboard.add_hotkey('ctrl+alt+x', self.emergency_stop, suppress=True)
        
        self.setup_ui()
        
        # Connect signals
        self.setup_signals()
        self.setup_menu()
        
        # Undo / redo shortcuts (Ctrl+Z / Ctrl+Y)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_steps)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo_steps)
        
    def _connect_step_signals(self, step):
        """Wire step widget signals for copy, undo, etc."""
        step.copyRequested.connect(self.copy_single_step)
        step.beforeDelete.connect(self._push_undo_state)
        step.beforeEditCommit.connect(self._push_undo_state)

    def _workflow_snapshot(self):
        """Deep copy of workflow state for undo/redo."""
        snap = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            w = self.steps_list.itemWidget(item)
            if w:
                snap.append({
                    "type": w.step_type,
                    "params": copy.deepcopy(w.params),
                })
        return snap

    def _restore_workflow_snapshot(self, snapshot):
        """Replace list widgets from a snapshot."""
        self._undo_in_progress = True
        try:
            self.steps_list.clear()
            for step_data in snapshot:
                step = AutomationStep(step_data["type"], copy.deepcopy(step_data["params"]))
                self._connect_step_signals(step)
                item = QListWidgetItem()
                item.setSizeHint(step.sizeHint())
                self.steps_list.addItem(item)
                self.steps_list.setItemWidget(item, step)
        finally:
            self._undo_in_progress = False

    def _push_undo_state(self):
        """Save current workflow before a change; clears redo."""
        if self._undo_in_progress:
            return
        self._undo_stack.append(self._workflow_snapshot())
        if len(self._undo_stack) > self._max_undo_steps:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        if hasattr(self, "undo_btn"):
            self.undo_btn.setEnabled(len(self._undo_stack) > 0)
        if hasattr(self, "redo_btn"):
            self.redo_btn.setEnabled(len(self._redo_stack) > 0)

    def undo_steps(self):
        """Restore previous workflow state."""
        if not self._undo_stack:
            return
        current = self._workflow_snapshot()
        prev = self._undo_stack.pop()
        self._redo_stack.insert(0, current)
        self._restore_workflow_snapshot(prev)
        self._update_undo_redo_buttons()

    def redo_steps(self):
        """Re-apply a undone change."""
        if not self._redo_stack:
            return
        current = self._workflow_snapshot()
        nxt = self._redo_stack.pop(0)
        self._undo_stack.append(current)
        self._restore_workflow_snapshot(nxt)
        self._update_undo_redo_buttons()

    def copy_selected_steps(self):
        """Copy selected steps to the clipboard"""
        # Get selected items
        selected_items = self.steps_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select one or more steps to copy")
            return
            
        # Clear previous copies
        self.copied_steps = []
        
        # Store the step data
        for item in selected_items:
            step_widget = self.steps_list.itemWidget(item)
            if step_widget:
                # Get the step data
                step_data = step_widget.get_data()
                self.copied_steps.append(step_data)
        
        # Show notification
        steps_count = len(self.copied_steps)
        QMessageBox.information(
            self, 
            "Steps Copied", 
            f"{steps_count} step{'s' if steps_count > 1 else ''} copied to clipboard"
        )
    
    def paste_steps(self):
        """Paste previously copied steps"""
        if not self.copied_steps:
            QMessageBox.information(self, "Nothing to Paste", "No steps have been copied")
            return
        
        self._push_undo_state()
            
        # Get current selection (where to paste)
        current_index = self.steps_list.currentRow()
        if current_index < 0:
            current_index = self.steps_list.count()  # Append at the end if no selection
            
        # Insert all copied steps
        for i, step_data in enumerate(self.copied_steps):
            # Create new widget
            step = AutomationStep(step_data["type"], copy.deepcopy(step_data["params"]))
            
            self._connect_step_signals(step)
            
            # Create list item
            item = QListWidgetItem()
            item.setSizeHint(step.sizeHint())
            
            # Insert at the appropriate position
            insert_position = current_index + i + 1
            self.steps_list.insertItem(insert_position, item)
            self.steps_list.setItemWidget(item, step)
            
        # Select the newly pasted items
        for i in range(len(self.copied_steps)):
            self.steps_list.item(current_index + i + 1).setSelected(True)
            
        # Notify user
        steps_count = len(self.copied_steps)
        QMessageBox.information(
            self, 
            "Steps Pasted", 
            f"{steps_count} step{'s' if steps_count > 1 else ''} pasted successfully"
        )
        
    def copy_single_step(self, step):
        """Copy a single step when the copy button is clicked"""
        # Clear previous copies
        self.copied_steps = []
        
        # Store the step data
        step_data = step.get_data()
        self.copied_steps.append(step_data)
        
        # Show notification (use status bar to be less intrusive)
        self.statusBar().showMessage(f"Step '{step_data['params'].get('name', 'Unnamed')}' copied to clipboard", 3000)
        
    def add_step(self):
        dialog = AddStepDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            step_type = dialog.get_selected_type()
            if step_type in STEP_DIALOGS:
                config_dialog = STEP_DIALOGS[step_type]()
                if config_dialog.exec() == QDialog.DialogCode.Accepted:
                    self._push_undo_state()
                    params = config_dialog.get_params()
                    step = AutomationStep(step_type, params)
                    self._connect_step_signals(step)
                    item = QListWidgetItem()
                    item.setSizeHint(step.sizeHint())
                    self.steps_list.addItem(item)
                    self.steps_list.setItemWidget(item, step)

    def setup_signals(self):
        # Recorder signals
        self.recorder.action_recorded.connect(self.on_action_recorded)
        self.recorder.recording_stopped.connect(self.on_recording_stopped)
        self.recorder.coordinate_recorded.connect(self.on_coordinate_recorded)
        self.recorder.recording_armed.connect(self.on_recording_armed_changed)
        
        # Executor signals
        self.executor.step_started.connect(self.on_step_started)
        self.executor.step_completed.connect(self.on_step_completed)
        self.executor.step_error.connect(self.on_step_error)
        self.executor.workflow_completed.connect(self.on_workflow_completed)
        self.executor.debug_info.connect(self.on_debug_info)  # Connect debug signal

    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(8)  # Reduced spacing
        main_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins

        # Create left panel (Steps List)
        left_panel = self.create_left_panel()
        
        # Create right panel (Configuration)
        right_panel = self.create_right_panel()
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 2)  # Increased ratio for left panel
        main_layout.addWidget(right_panel, 1)  # Decreased ratio for right panel

    def create_left_panel(self):
        """Create the left panel with workflow steps"""
        left_panel = QWidget()
        layout = QVBoxLayout(left_panel)

        # Settings group
        settings_group = QGroupBox("⚙️ Settings")
        settings_layout = QVBoxLayout()

        # Debug mode checkbox with icon
        self.debug_mode = QCheckBox("🔍 Debug Mode")
        self.debug_mode.setChecked(True)
        self.debug_mode.toggled.connect(self.toggle_debug_mode)
        settings_layout.addWidget(self.debug_mode)

        # Add settings to group
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Steps list
        steps_group = QGroupBox("📋 Workflow Steps")
        steps_layout = QVBoxLayout()
        
        self.steps_list = StepsListWidget()
        # Enable multiple selection
        self.steps_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.steps_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.steps_list.model().rowsMoved.connect(self._on_steps_reordered)
        self.steps_list.beforeReorder.connect(self._push_undo_state)
        steps_layout.addWidget(self.steps_list)
        
        # Add button layout for step operations
        step_buttons_layout = QHBoxLayout()
        
        self.undo_btn = QPushButton("↩️ Undo")
        self.undo_btn.setToolTip("Undo last change (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.undo_steps)
        self.undo_btn.setEnabled(False)
        step_buttons_layout.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("↪️ Redo")
        self.redo_btn.setToolTip("Redo (Ctrl+Y)")
        self.redo_btn.clicked.connect(self.redo_steps)
        self.redo_btn.setEnabled(False)
        step_buttons_layout.addWidget(self.redo_btn)
        
        # Copy steps button
        copy_steps_btn = QPushButton("📋 Copy Selected")
        copy_steps_btn.clicked.connect(self.copy_selected_steps)
        copy_steps_btn.setToolTip("Copy selected steps (Ctrl+click to select multiple)")
        step_buttons_layout.addWidget(copy_steps_btn)
        
        # Paste steps button
        paste_steps_btn = QPushButton("📋 Paste Steps")
        paste_steps_btn.clicked.connect(self.paste_steps)
        paste_steps_btn.setToolTip("Paste copied steps")
        step_buttons_layout.addWidget(paste_steps_btn)
        
        steps_layout.addLayout(step_buttons_layout)
        
        steps_group.setLayout(steps_layout)
        layout.addWidget(steps_group)

        return left_panel

    def create_right_panel(self):
        """Create the right panel with debug output"""
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)

        # Create tabs
        tabs = QTabWidget()
        
        # Debug tab
        debug_tab = QWidget()
        debug_layout = QVBoxLayout(debug_tab)
        
        # Debug controls
        debug_controls = QHBoxLayout()
        
        # Clear log button
        clear_btn = QPushButton("🧹 Clear Log")
        clear_btn.clicked.connect(self.clear_debug_log)
        debug_controls.addWidget(clear_btn)
        
        # Open debug folder button
        open_folder_btn = QPushButton("📁 Open Debug Folder")
        open_folder_btn.clicked.connect(self.open_debug_directory)
        debug_controls.addWidget(open_folder_btn)
        
        open_logs_btn = QPushButton("📄 Open Execution Logs")
        open_logs_btn.setToolTip("Plain-text log file for each workflow run")
        open_logs_btn.clicked.connect(self.open_logs_directory)
        debug_controls.addWidget(open_logs_btn)
        
        debug_layout.addLayout(debug_controls)
        
        # Debug output
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        debug_layout.addWidget(self.debug_text)
        
        tabs.addTab(debug_tab, "🔍 Debug")
        
        layout.addWidget(tabs)
        
        # Workflow controls
        controls_group = QGroupBox("Workflow Controls")
        controls_layout = QVBoxLayout()
        
        # Add step and record buttons
        top_controls = QHBoxLayout()
        
        # Add step button
        add_step_btn = QPushButton("➕ Add Step")
        add_step_btn.clicked.connect(self.add_step)
        top_controls.addWidget(add_step_btn)
        
        # Record button
        record_btn = QPushButton("⏺️ Record")
        record_btn.setCheckable(True)
        record_btn.clicked.connect(self.toggle_coordinate_recording)
        top_controls.addWidget(record_btn)
        self.record_btn = record_btn  # Store as instance variable
        
        controls_layout.addLayout(top_controls)
        
        # Loop count control
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("Loop Count:"))
        self.loop_count = QSpinBox()
        self.loop_count.setRange(1, 999)
        self.loop_count.setValue(1)
        self.loop_count.setToolTip("Number of times to repeat the workflow")
        loop_layout.addWidget(self.loop_count)
        controls_layout.addLayout(loop_layout)
        
        # Run controls
        run_layout = QHBoxLayout()
        
        # Run button
        run_btn = QPushButton("▶️ Run")
        run_btn.clicked.connect(self.run_workflow)
        run_layout.addWidget(run_btn)
        
        # Stop button
        self.stop_btn = QPushButton("⏹️ Stop")  # Store as instance variable
        self.stop_btn.clicked.connect(self.stop_workflow)
        run_layout.addWidget(self.stop_btn)
        
        # Resume button
        self.resume_btn = QPushButton("⏯️ Resume")
        self.resume_btn.clicked.connect(self.resume_workflow)
        run_layout.addWidget(self.resume_btn)
        
        # Pause button
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(self.toggle_pause)
        run_layout.addWidget(self.pause_btn)
        
        controls_layout.addLayout(run_layout)
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        return right_panel

    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("📂 File")
        
        new_action = file_menu.addAction("🆕 New")
        new_action.triggered.connect(self.new_automation)
        
        save_action = file_menu.addAction("💾 Save")
        save_action.triggered.connect(self.save_automation)
        
        load_action = file_menu.addAction("📂 Load")
        load_action.triggered.connect(self.load_automation)
        
        # Add separator before Quit
        file_menu.addSeparator()
        
        # Add Quit action
        quit_action = file_menu.addAction("❌ Quit")
        quit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menubar.addMenu("🔧 Tools")
        
        self.record_action = tools_menu.addAction("⏺️ Start Recording")
        self.record_action.triggered.connect(self.toggle_recording)
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        general_help_action = help_menu.addAction("📚 User Guide")
        general_help_action.triggered.connect(self.show_general_help)
        
        steps_help_action = help_menu.addAction("🔍 Automation Steps")
        steps_help_action.triggered.connect(self.show_steps_help)
        
        recording_help_action = help_menu.addAction("⏺️ Recording Guide")
        recording_help_action.triggered.connect(self.show_recording_help)
        
        help_menu.addSeparator()
        
        about_action = help_menu.addAction("ℹ️ About")
        about_action.triggered.connect(self.show_about)

    def new_automation(self):
        if self.steps_list.count():
            self._push_undo_state()
        self.steps_list.clear()
        self.current_workflow_path = None
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def save_automation(self):
        """Save the current automation workflow"""
        if len(self.steps_list) == 0:
            QMessageBox.warning(self, "No Steps", "No steps to save. Add some automation steps first.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Automation Workflow",
            os.path.join(AUTOMATIONS_DIR, "automation.json"),
            "JSON Files (*.json)"
        )
        
        if file_name:
            # Ensure file has .json extension
            if not file_name.lower().endswith('.json'):
                file_name += '.json'
                
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_name), exist_ok=True)
                
                # Collect data from steps
                workflow = {
                    "version": "1.0",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "debug_mode": self.debug_mode.isChecked(),
                    "steps": []
                }
                
                for i in range(self.steps_list.count()):
                    item = self.steps_list.item(i)
                    step_widget = self.steps_list.itemWidget(item)
                    
                    if step_widget:
                        workflow["steps"].append({
                            "type": step_widget.step_type,
                            "params": step_widget.params
                        })
                
                with open(file_name, 'w') as f:
                    json.dump(workflow, f, indent=4)
                
                self.current_workflow_path = file_name
                QMessageBox.information(self, "Success", "Automation saved successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save automation: {str(e)}")

    def load_automation(self):
        """Load automation workflow from a JSON file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Automation", AUTOMATIONS_DIR, "JSON Files (*.json)"
        )
        
        if not file_name:
            return
            
        try:
            with open(file_name, 'r') as file:
                data = json.load(file)
                
            # Check if the file has the expected format
            if "steps" not in data:
                QMessageBox.warning(self, "Invalid File", "The selected file is not a valid automation workflow.")
                return
                
            # Clear current workflow
            self.steps_list.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._update_undo_redo_buttons()
            
            skipped = 0
            # Add steps from the file
            for step_data in data["steps"]:
                stype = step_data.get("type")
                if stype not in STEP_DIALOGS:
                    skipped += 1
                    continue
                # Create step widget
                step = AutomationStep(stype, copy.deepcopy(step_data.get("params", {})))
                self._connect_step_signals(step)
                
                # Add to list
                item = QListWidgetItem()
                item.setSizeHint(step.sizeHint())
                self.steps_list.addItem(item)
                self.steps_list.setItemWidget(item, step)
                
            # Save the current workflow path
            self.current_workflow_path = file_name
            
            # Update window title
            file_base = os.path.basename(file_name)
            self.setWindowTitle(f"Automation Tool - {file_base}")
            
            # Show success message
            msg = f"Loaded {self.steps_list.count()} steps from {file_base}"
            if skipped:
                msg += f"\n\n({skipped} step(s) skipped — removed or unknown step types.)"
            QMessageBox.information(self, "Workflow Loaded", msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Workflow", f"Failed to load workflow: {str(e)}")
            logging.error(f"Error loading workflow: {str(e)}")

    def toggle_recording(self):
        """Handle recording button in menu"""
        if not self.recorder.is_recording:
            # Show countdown dialog
            countdown_dialog = QDialog(self)
            countdown_dialog.setWindowTitle("Recording will start in...")
            countdown_dialog.setFixedSize(300, 150)
            layout = QVBoxLayout(countdown_dialog)
            
            # Countdown label with large font
            countdown_label = QLabel("10")
            countdown_label.setStyleSheet("font-size: 48pt; color: #FF4444; font-weight: bold;")
            countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(countdown_label)
            
            # Instructions label
            instructions = QLabel("Press ESC anytime to stop recording")
            instructions.setStyleSheet("color: #e0e0e0;")
            instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(instructions)
            
            countdown_dialog.show()
            
            # Countdown timer
            for i in range(10, 0, -1):
                countdown_label.setText(str(i))
                QApplication.processEvents()
                # Play notification sound (Windows beep)
                if sys.platform == 'win32':
                    self._safe_beep(1000, 100)
                time.sleep(1)
            
            countdown_dialog.close()
            
            # Play start recording sound (longer beep)
            if sys.platform == 'win32':
                self._safe_beep(2000, 500)
            
            # Start recording and setup stop shortcut
            self.recorder.start_recording()
            self.record_action.setText("⏹️ Stop Recording (ESC)")
            self.record_stop_hotkey = keyboard.add_hotkey('esc', self.stop_recording, suppress=True)
        else:
            self.stop_recording()

    def stop_recording(self):
        """Stop recording and cleanup"""
        if self.recorder.is_recording:
            self.recorder.stop_recording()
            self.record_action.setText("⏺️ Start Recording")
            if self.record_stop_hotkey is not None:
                try:
                    keyboard.remove_hotkey(self.record_stop_hotkey)
                except Exception as e:
                    logging.debug(f"Failed to remove ESC hotkey cleanly: {e}")
                finally:
                    self.record_stop_hotkey = None
            # Play stop recording sound
            if sys.platform == 'win32':
                self._safe_beep(500, 500)

    def _safe_beep(self, frequency, duration_ms):
        """Play a system beep without crashing if audio is unavailable."""
        try:
            import winsound
            winsound.Beep(frequency, duration_ms)
        except Exception as e:
            logging.warning(f"Beep failed (freq={frequency}, duration={duration_ms}): {e}")

    def on_action_recorded(self, step_type, params):
        self._push_undo_state()
        step = AutomationStep(step_type, copy.deepcopy(params))
        self._connect_step_signals(step)
        item = QListWidgetItem()
        item.setSizeHint(step.sizeHint())
        self.steps_list.addItem(item)
        self.steps_list.setItemWidget(item, step)

    def on_recording_stopped(self):
        self.record_action.setText("⏺️ Start Recording")

    def run_workflow(self):
        """Run the current workflow"""
        if not self.steps_list.count():
            QMessageBox.warning(self, "No Steps", "Please add some steps to the workflow first.")
            return

        # Create progress dialog
        self.progress_dialog = QProgressDialog("Preparing to run workflow...", "Cancel", 0, self.steps_list.count(), self)
        self.progress_dialog.setWindowTitle("Running Workflow")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        
        # Get all steps
        steps = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            widget = self.steps_list.itemWidget(item)
            if widget:
                step_data = widget.get_data()
                steps.append(step_data)

        if not steps:
            self.progress_dialog.close()
            self.progress_dialog = None
            return

        # Create and start executor thread
        self.executor = WorkflowExecutor()
        self.executor_thread = ExecutorThread(self.executor, steps)
        
        # Connect signals
        self.executor.step_started.connect(self.on_step_started)
        self.executor.step_completed.connect(self.on_step_completed)
        self.executor.step_error.connect(self.on_step_error)
        self.executor.workflow_completed.connect(self.on_workflow_completed)
        self.executor.debug_info.connect(self.on_debug_info)
        self.executor_thread.finished.connect(self.on_executor_thread_finished)
        
        # Set debug mode
        self.executor.debug_mode = self.debug_mode.isChecked()
        
        # Get loop count
        loop_count = self.loop_count.value()
        
        # Start execution
        self.executor_thread.start(loop_count)
        
        # Update UI state
        self.pause_btn.setEnabled(True)
        self.pause_btn.setChecked(False)
        self.pause_btn.setText("⏸️ Pause")

    def on_step_started(self, step_index, step_type):
        """Handle step started signal"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(f"Executing step {step_index + 1}: {step_type}")
            self.progress_dialog.setValue(step_index)

    def on_step_completed(self, step_index):
        """Handle step completed signal"""
        if self.progress_dialog:
            self.progress_dialog.setValue(step_index + 1)

    def on_step_error(self, step_index, error):
        """Handle step error signal"""
        QMessageBox.critical(
            self,
            "Error",
            f"Error executing step {step_index + 1}:\n{error}"
        )
        if self.progress_dialog:
            self.progress_dialog.cancel()
            self.progress_dialog = None
        
        # Reset UI state
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)

    def on_workflow_completed(self):
        """Handle workflow completed signal"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)

    def on_executor_thread_finished(self):
        """Handle executor thread finished signal"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)

    def toggle_debug_mode(self, state):
        """Toggle debug mode"""
        self.executor.debug_mode = bool(state)
        self.debug_text.append(f"Debug mode {'enabled' if state else 'disabled'}")

    def clear_debug_log(self):
        """Clear the debug log"""
        self.debug_text.clear()

    def open_debug_directory(self):
        """Open the debug directory in file explorer"""
        try:
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)), "debug")
            if os.path.exists(debug_dir):
                # Use os.startfile for Windows
                if sys.platform == 'win32':
                    os.startfile(debug_dir)
                # Use xdg-open for Linux
                elif sys.platform == 'linux':
                    os.system(f'xdg-open "{debug_dir}"')
                # Use open for macOS
                elif sys.platform == 'darwin':
                    os.system(f'open "{debug_dir}"')
            else:
                QMessageBox.warning(self, "Directory Not Found", 
                    "Debug directory does not exist. It will be created when you run an automation.")
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                f"Could not open debug directory: {str(e)}")

    def open_logs_directory(self):
        """Open the folder containing per-run execution log files (plain text)."""
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
            if os.path.exists(LOGS_DIR):
                if sys.platform == 'win32':
                    os.startfile(LOGS_DIR)
                elif sys.platform == 'linux':
                    os.system(f'xdg-open "{LOGS_DIR}"')
                elif sys.platform == 'darwin':
                    os.system(f'open "{LOGS_DIR}"')
            else:
                QMessageBox.warning(self, "Directory Not Found", "Logs directory could not be created.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open logs directory: {str(e)}")

    def pause_workflow(self):
        """Pause the current workflow"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor.pause()
            self.debug_text.append("Workflow paused")

    def resume_workflow(self):
        """Resume the current workflow"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor.resume()
            self.debug_text.append("Workflow resumed")

    def toggle_pause(self):
        """Toggle between pause and resume states"""
        if self.executor_thread and self.executor_thread.isRunning():
            if self.pause_btn.isChecked():
                self.pause_workflow()
                self.pause_btn.setText("⏯️ Resume")
            else:
                self.resume_workflow()
                self.pause_btn.setText("⏸️ Pause")

    def stop_workflow(self):
        """Stop the current workflow execution"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor.stop()
            self.executor_thread.wait()
            self.debug_text.append("Workflow stopped")
            
            # Clean up progress dialog if it exists
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # Reset UI state
            self.pause_btn.setEnabled(False)
            self.pause_btn.setChecked(False)
            self.pause_btn.setText("⏸️ Pause")

    def on_debug_info(self, info):
        """Handle debug information from executor"""
        # Format the message with timestamp and appropriate color coding
        timestamp = time.strftime("%H:%M:%S")
        
        # Color coding based on message content
        if "✓" in info:  # Success messages
            formatted_msg = f'<span style="color: #00FF00;">[{timestamp}] {info}</span>'
        elif "❌" in info:  # Error messages
            formatted_msg = f'<span style="color: #FF0000;">[{timestamp}] {info}</span>'
        elif "===" in info:  # Step headers
            formatted_msg = f'<span style="color: #00FFFF;">[{timestamp}] {info}</span>'
        elif "Warning" in info:  # Warnings
            formatted_msg = f'<span style="color: #FFA500;">[{timestamp}] {info}</span>'
        else:  # Regular debug messages
            formatted_msg = f'<span style="color: #FFFFFF;">[{timestamp}] {info}</span>'
        
        # Add the message to the debug text area
        self.debug_text.append(formatted_msg)
        
        # Scroll to the bottom to show the latest message
        self.debug_text.verticalScrollBar().setValue(
            self.debug_text.verticalScrollBar().maximum()
        )
        
        # Update the application to ensure the UI remains responsive
        QApplication.processEvents()

    def closeEvent(self, event):
        """Handle application close event"""
        # Remove fail-safe shortcut
        keyboard.remove_hotkey('ctrl+alt+x')
        self.stop_workflow()
        event.accept()

    def toggle_coordinate_recording(self):
        """Toggle coordinate recording mode"""
        if not self.coordinate_recording:
            # Show instructions
            QMessageBox.information(
                self,
                "Record Coordinates",
                "1. Click 'OK' to start recording\n"
                "2. Press Ctrl+Shift+F8 to capture coordinates\n"
                "3. Press ESC to cancel"
            )
            
            # Start recording
            self.coordinate_recording = True
            self.recorder.start_coordinate_recording()
            
            # Visual feedback
            if hasattr(self, 'record_btn') and self.record_btn:
                self.record_btn.setStyleSheet("background-color: #FFA500;")  # Orange for recording state
            
            # Update status
            self.statusBar().showMessage("Recording armed - Press Ctrl+Shift+F8 when ready to capture coordinates")
            
            # Set up ESC key to cancel recording
            keyboard.on_press_key('esc', lambda _: self.cancel_coordinate_recording())
        else:
            self.cancel_coordinate_recording()

    def cancel_coordinate_recording(self):
        """Cancel coordinate recording mode"""
        if self.coordinate_recording:
            # Stop recording
            self.coordinate_recording = False
            self.recorder.stop_coordinate_recording()
            
            # Reset UI
            if hasattr(self, 'record_btn') and self.record_btn:
                self.record_btn.setStyleSheet("")  # Reset to default style
                self.record_btn.setChecked(False)
            
            # Update status
            self.statusBar().showMessage("Recording stopped", 3000)

    def on_recording_armed_changed(self, armed):
        """Handle recording armed state change"""
        # Find and update the record button
        for widget in self.findChildren(QPushButton):
            if widget.text() == "⏺️ Record":
                if armed:
                    widget.setStyleSheet("background-color: #FFA500;")  # Orange for armed state
                    self.statusBar().showMessage("Recording armed - Press Ctrl+Shift+F8 when ready to capture coordinates")
                else:
                    widget.setStyleSheet("")  # Reset to default style
                    self.statusBar().clearMessage()
                break

    def on_coordinate_recorded(self, x, y):
        """Handle recorded coordinates"""
        if self.coordinate_recording:
            # Update the currently selected step with new coordinates
            current_item = self.steps_list.currentItem()
            if current_item:
                step_widget = self.steps_list.itemWidget(current_item)
                if step_widget:
                    if step_widget.step_type == StepType.MOUSE_CLICK:
                        # Handle mouse click coordinates
                        old_coords = (step_widget.params.get("x"), step_widget.params.get("y"))
                        step_widget.update_params({
                            "click_type": "coordinates",
                            "x": x,
                            "y": y
                        })
                        message = (
                            f"Coordinates recorded for step: {step_widget.params.get('name', 'Unnamed Step')}\n"
                            f"New coordinates: ({x}, {y})\n"
                        )
                        if old_coords[0] is not None:
                            message += f"Previous coordinates: ({old_coords[0]}, {old_coords[1]})"
                    else:
                        message = f"Coordinates recorded: ({x}, {y})"
                    
                    QMessageBox.information(
                        self,
                        "Coordinates Recorded",
                        message
                    )
                    
                    # Remind to save if workflow has changed
                    if self.current_workflow_path:
                        self.statusBar().showMessage("Remember to save your workflow to keep these coordinates!", 5000)
            
            # Reset recording state
            self.coordinate_recording = False
            self.recorder.stop_coordinate_recording()

    def _cleanup_invalid_items(self):
        """Clean up any invalid or empty items in the list"""
        items_to_remove = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            if not item or not self.steps_list.itemWidget(item):
                items_to_remove.append(i)
        
        # Remove items in reverse order to maintain correct indices
        for i in reversed(items_to_remove):
            self.steps_list.takeItem(i)

    def _on_steps_reordered(self, parent, start, end, destination, row):
        """Handle steps reordering after drag and drop"""
        # Clean up any invalid items that might have been created during drag and drop
        self._cleanup_invalid_items()
        
        # Ensure all remaining items have valid widgets
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            if item and not self.steps_list.itemWidget(item):
                # If we find an item without a widget, remove it
                self.steps_list.takeItem(i)

    def show_general_help(self):
        """Show general help dialog"""
        dialog = GeneralHelpDialog(self)
        dialog.exec()
        
    def show_steps_help(self):
        """Show steps help dialog"""
        dialog = StepsHelpDialog(self)
        dialog.exec()
        
    def show_recording_help(self):
        """Show recording help dialog"""
        dialog = RecordingHelpDialog(self)
        dialog.exec()
        
    def show_about(self):
        """Show about dialog"""
        dialog = AboutDialog(self)
        dialog.exec()

    def emergency_stop(self):
        """Emergency stop for the automation workflow"""
        try:
            if hasattr(self, 'executor') and self.executor:
                self.executor.stop()
            
            if hasattr(self, 'executor_thread') and self.executor_thread and self.executor_thread.isRunning():
                self.executor_thread.quit()
                # Give it a short time to quit gracefully
                if not self.executor_thread.wait(1000):  # Wait up to 1 second
                    self.executor_thread.terminate()  # Force quit if necessary
            
            # Reset UI state
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            
            # Clear any highlighted steps
            for i in range(self.steps_list.count()):
                item = self.steps_list.item(i)
                widget = self.steps_list.itemWidget(item)
                if widget:
                    widget.setStyleSheet("")
            
            QMessageBox.information(self, "Automation Stopped", 
                "The automation has been stopped.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                f"Error during emergency stop: {str(e)}")
            # Ensure UI is reset even if there's an error
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

# Add the help dialog base class and specialized dialogs
class HelpDialog(QDialog):
    """Base class for help dialogs"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Help text
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                font-family: system;
                font-size: 10pt;
                padding: 10px;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.help_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def set_help_content(self, html_content):
        self.help_text.setHtml(html_content)

class GeneralHelpDialog(HelpDialog):
    """Dialog for general user guide"""
    def __init__(self, parent=None):
        super().__init__("User Guide", parent)
        
        content = """
        <h1>🤖 Automation Tool User Guide</h1>
        
        <h2>Introduction</h2>
        <p>The Automation Tool allows you to create, save, load, and execute automation workflows for repetitive tasks.</p>
        
        <h2>Safety Features</h2>
        <p><b>⚠️ Emergency Stop:</b> Press <span style="color: #FF4444; font-weight: bold;">Ctrl+Alt+X</span> at any time to immediately stop a running automation. Use this fail-safe shortcut if something goes wrong or you need to stop the automation quickly.</p>
        
        <h2>Main Interface Components</h2>
        <ul>
            <li><b>Left Panel (Workflow):</b> Contains your workflow steps list with a wider view for better readability</li>
            <li><b>Right Panel (Debug/Controls):</b> Contains debug console and workflow controls in a compact layout</li>
        </ul>
        
        <h2>Creating a Workflow</h2>
        <ol>
            <li>Click the "➕ Add Step" button in the right panel to add a new step to your workflow</li>
            <li>Select the desired step type from the dropdown menu</li>
            <li>Configure the step's parameters in the dialog that appears</li>
            <li>Repeat to build your complete workflow</li>
        </ol>
        
        <h2>Running a Workflow</h2>
        <ol>
            <li>Ensure all steps are properly configured</li>
            <li>Set the number of times to loop the workflow (default is 1)</li>
            <li>Click the "▶️ Run" button to execute the workflow</li>
            <li>Monitor progress in the debug console</li>
            <li>Use "⏸️ Pause", "⏯️ Resume", or "⏹️ Stop" buttons to control execution</li>
        </ol>
        
        <h2>Recording Actions</h2>
        <p>You can record mouse clicks and keyboard inputs by using the Record function:</p>
        <ol>
            <li>Click the "⏺️ Start Recording" option in the Tools menu or click the "⏺️ Record" button</li>
            <li>Perform the actions you want to record</li>
            <li>Click "⏹️ Stop Recording" when finished</li>
        </ol>
        
        <h2>Saving and Loading Workflows</h2>
        <ol>
            <li>Use "💾 Save" in the File menu to save your workflow</li>
            <li>Use "📂 Load" to load a previously saved workflow</li>
            <li>Use "🆕 New" to start a fresh workflow</li>
        </ol>
        
        <h2>Debug Mode</h2>
        <p>Enable Debug Mode to see detailed information during workflow execution:</p>
        <ul>
            <li>Detailed logs appear in the Debug Console</li>
            <li>Each run also writes a <b>plain-text execution log</b> file in the logs folder</li>
            <li>Use "🧹 Clear Log" to clear the on-screen console</li>
            <li>Use "📄 Open Execution Logs" to open the folder with per-run log files</li>
            <li>Use "📁 Open Debug Folder" for the app debug folder (e.g. automation.log)</li>
        </ul>
        
        <h2>Undo / Redo</h2>
        <p>Use <b>↩️ Undo</b> and <b>↪️ Redo</b> below the step list (or Ctrl+Z / Ctrl+Y) to revert or re-apply changes to steps.</p>
        
        <h2>Tips for Success</h2>
        <ul>
            <li>Test your workflow on a small scale before running it on important data</li>
            <li>Always save your workflow before running long automations</li>
            <li>Use descriptive names for your steps to make them easier to understand</li>
            <li>If a step isn't working correctly, try recording it again or adjusting its parameters</li>
            <li>For repetitive tasks, use the loop count feature instead of duplicating steps</li>
            <li>When typing text in multiple iterations, consider using the multiple text inputs feature</li>
        </ul>
        """
        
        self.set_help_content(content)

class StepsHelpDialog(HelpDialog):
    """Dialog for automation steps documentation"""
    def __init__(self, parent=None):
        super().__init__("Automation Steps Guide", parent)
        
        content = """
        <h1>📋 Automation Steps Documentation</h1>
        
        <h2>Mouse Click Step</h2>
        <p><b>Purpose:</b> Perform a mouse click at specific coordinates or on an image.</p>
        <p><b>Parameters:</b></p>
        <ul>
            <li><b>Click Type:</b> Choose between coordinate-based or image-based clicking</li>
            <li><b>Mouse Button:</b> Select left or right mouse button</li>
            <li><b>Coordinates:</b> Specify X and Y screen coordinates (for coordinate-based clicks)</li>
            <li><b>Image Path:</b> Path to the reference image (for image-based clicks)</li>
            <li><b>Confidence:</b> Matching threshold for image recognition (0.1-1.0)</li>
            <li><b>Duration:</b> How long the mouse movement takes (in seconds)</li>
            <li><b>Text Input After Click:</b> Optional text to type after clicking</li>
            <li><b>Delay Before Typing:</b> Wait time before typing (in seconds)</li>
            <li><b>Special Key:</b> Optional special key to press after typing (Enter, Tab, etc.)</li>
        </ul>
        <p><b>Example:</b> Click on the login button and enter username</p>
        <pre>
        Step Name: "Click Login Button and Enter Username"
        Click Type: Image-based
        Mouse Button: Left Click
        Image Path: "login_button.png"
        Confidence: 0.9
        Text Input After Click: Enabled
        Text to Type: "admin"
        Delay Before Typing: 0.5 seconds
        Special Key: Tab (to move to password field)
        </pre>
        
        <h2>Keyboard Type Step</h2>
        <p><b>Purpose:</b> Type text at the current cursor position with support for multiple text inputs.</p>
        <p><b>Parameters:</b></p>
        <ul>
            <li><b>Input Type:</b> Choose between single text or multiple text inputs</li>
            <li><b>Text Input:</b> The text to type (single input) or list of texts (multiple inputs)</li>
            <li><b>Special Key:</b> Optional special key to press after typing</li>
            <li><b>Delay:</b> Delay between keystrokes (in seconds)</li>
        </ul>
        <p><b>Example 1:</b> Type a single search query and press Enter</p>
        <pre>
        Step Name: "Search for Product"
        Input Type: Single
        Text Input: "wireless headphones"
        Special Key: Enter
        Delay: 0.1 seconds
        </pre>
        <p><b>Example 2:</b> Type multiple product codes in a loop</p>
        <pre>
        Step Name: "Enter Product Codes"
        Input Type: Multiple
        Text List: ["ABC123", "XYZ789", "DEF456"]
        Special Key: Enter
        Delay: 0.1 seconds
        </pre>
        <p>When using multiple text inputs, the step will:</p>
        <ul>
            <li>Cycle through the list of texts in order</li>
            <li>Work seamlessly with workflow loops</li>
            <li>Type each text in sequence without clearing previous text</li>
        </ul>
        
        <h2>Keyboard Special Step</h2>
        <p><b>Purpose:</b> Execute keyboard shortcuts or special key combinations.</p>
        <p><b>Parameters:</b></p>
        <ul>
            <li><b>Key:</b> The main key to press</li>
            <li><b>Modifiers:</b> Combination of Ctrl, Alt, Shift, and/or Windows keys</li>
        </ul>
        <p><b>Example:</b> Press Ctrl+C to copy selected content</p>
        <pre>
        Step Name: "Copy Selection"
        Key: C
        Modifiers: Ctrl
        </pre>
        <p><b>Example:</b> Press Alt+Tab to switch applications</p>
        <pre>
        Step Name: "Switch Applications"
        Key: Tab
        Modifiers: Alt
        </pre>
        
        <h2>Wait Step</h2>
        <p><b>Purpose:</b> Pause execution for a specified duration.</p>
        <p><b>Parameters:</b></p>
        <ul>
            <li><b>Duration:</b> Time to wait (in seconds)</li>
        </ul>
        <p><b>Example:</b> Wait for page to load</p>
        <pre>
        Step Name: "Wait for Page Load"
        Duration: 3 seconds
        </pre>
        
        <h2>Wait for Image</h2>
        <p><b>Purpose:</b> Pause until a reference image is detected on screen (same matching approach as image-based mouse click), then continue.</p>
        <p><b>Parameters:</b></p>
        <ul>
            <li><b>Step Name:</b> Label for this step</li>
            <li><b>Include in workflow loop:</b> Whether the step runs every main iteration or only once</li>
            <li><b>Reference image:</b> PNG/JPEG to match on screen</li>
            <li><b>Confidence threshold (%):</b> Minimum match score (1–100)</li>
            <li><b>Timeout (seconds):</b> Fail the step if the image does not appear in time</li>
        </ul>
        
        <h2>Wait for Image to Disappear</h2>
        <p><b>Purpose:</b> Pause until the reference image is no longer matched on screen (e.g. loading spinner gone), then continue. Same parameters as <b>Wait for Image</b>.</p>
        
        """
        
        self.set_help_content(content)

class RecordingHelpDialog(HelpDialog):
    """Dialog for recording guide"""
    def __init__(self, parent=None):
        super().__init__("Recording Guide", parent)
        
        content = """
        <h1>⏺️ Recording Guide</h1>
        
        <h2>Action Recording</h2>
        <p>Action recording allows you to create automation steps by performing the actions yourself:</p>
        
        <h3>How to Record Actions</h3>
        <ol>
            <li>Click the "⏺️ Start Recording" option in the Tools menu or click the "⏺️ Record" button</li>
            <li>Perform the actions you want to automate (mouse clicks, keyboard typing, etc.)</li>
            <li>Click "⏹️ Stop Recording" when finished</li>
        </ol>
        
        <p><b>Recorded Actions Include:</b></p>
        <ul>
            <li>Mouse clicks (with coordinates)</li>
            <li>Keyboard typing (text input)</li>
            <li>Special key presses</li>
        </ul>
        
        <p><b>Example:</b> Recording a login sequence</p>
        <ol>
            <li>Start recording</li>
            <li>Click on the username field</li>
            <li>Type your username</li>
            <li>Press Tab to move to the password field</li>
            <li>Type your password</li>
            <li>Click the login button</li>
            <li>Stop recording</li>
        </ol>
        
        <h2>Coordinate Recording</h2>
        <p>Coordinate recording allows you to update the coordinates for an existing step:</p>
        
        <h3>How to Record Coordinates</h3>
        <ol>
            <li>Select the step you want to update in the workflow list</li>
            <li>Click the "⏺️ Record" button at the bottom of the steps list</li>
            <li>Position your mouse where you want to click</li>
            <li>Press Ctrl+Shift+F8 to capture the coordinates</li>
        </ol>
        
        <p><b>Example:</b> Updating click coordinates for a button that moved</p>
        <ol>
            <li>Select the "Click Login Button" step in your workflow</li>
            <li>Click "⏺️ Record"</li>
            <li>Position your mouse over the login button's new position</li>
            <li>Press Ctrl+Shift+F8</li>
            <li>The step will be updated with the new coordinates</li>
        </ol>
        
        <h2>Recording Tips</h2>
        <ul>
            <li><b>Move deliberately:</b> Make your mouse movements and clicks deliberate and clear</li>
            <li><b>Take your time:</b> Don't rush through the actions as the recorder needs time to process each action</li>
            <li><b>Review recorded steps:</b> After recording, review each step and edit if necessary</li>
            <li><b>Test the workflow:</b> Run the recorded workflow to ensure it works as expected</li>
            <li><b>Edit parameters manually:</b> You can fine-tune the recorded steps by clicking the "✏️ Edit" button</li>
        </ul>
        
        <h2>Keyboard Recording</h2>
        <p>The recorder captures text as you type it, but there are some special considerations:</p>
        <ul>
            <li>Special keys (Enter, Tab, etc.) are recorded as separate steps</li>
            <li>Key combinations (Ctrl+C, Alt+Tab, etc.) are recorded as Keyboard Special steps</li>
            <li>If you need to type slowly or with specific timing, edit the delay parameter after recording</li>
        </ul>
        """
        
        self.set_help_content(content)

class AboutDialog(QDialog):
    """Dialog showing information about the application"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Automation Tool")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)  # Increase spacing between elements

        # Title and Version
        title_label = QLabel("Automation Tool")
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #88CCFF;")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        version_label = QLabel("Version 2.0")
        version_label.setStyleSheet("font-size: 14pt; color: #00FF00;")
        layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # New Features Section
        new_features_group = QGroupBox("What's New in Version 2.0")
        new_features_layout = QVBoxLayout()
        
        features_text = QLabel(
            "• Interactive Mode for Mouse Clicks\n"
            "  - Scroll pages using arrow keys\n"
            "  - Click when ready using Space/Enter\n"
            "  - Skip steps with Escape key\n\n"
            "• Undo / Redo for workflow steps\n"
            "  - Revert or re-apply step list changes\n\n"
            "• Improved User Interface\n"
            "  - Clearer step configuration\n"
            "  - Better error handling\n"
            "  - Enhanced debug information"
        )
        features_text.setStyleSheet("color: #e0e0e0; font-size: 11pt;")
        new_features_layout.addWidget(features_text)
        new_features_group.setLayout(new_features_layout)
        layout.addWidget(new_features_group)

        # Description
        description = QLabel(
            "A powerful automation tool for creating and running custom workflows.\n"
            "Automate repetitive tasks with mouse clicks, keyboard input, and image recognition."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #e0e0e0; font-size: 11pt;")
        layout.addWidget(description, alignment=Qt.AlignmentFlag.AlignCenter)

        # Copyright
        copyright_label = QLabel("© 2024 All rights reserved")
        copyright_label.setStyleSheet("color: #888888;")
        layout.addWidget(copyright_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 20px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #4e4e4e;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Set dialog style
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 1em;
                padding: 10px;
                color: #88CCFF;
                font-size: 12pt;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

        # Set fixed size for the dialog
        self.setFixedSize(500, 600)

if __name__ == '__main__':
    # Suppress Qt DPI warnings
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"  # Suppress DPI warning messages
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    window = AutomationToolGUI()
    window.show()
    sys.exit(app.exec())
