from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QFileDialog,
    QRadioButton, QButtonGroup, QGroupBox, QTabWidget, QWidget,
    QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
import json
import logging

class StepType:
    MOUSE_CLICK = "Mouse Click"
    KEYBOARD_TYPE = "Keyboard Type"
    KEYBOARD_SPECIAL = "Keyboard Special"
    WAIT = "Wait"
    WAIT_FOR_IMAGE = "Wait for Image"
    WAIT_FOR_IMAGE_DISAPPEAR = "Wait for Image to Disappear"
    LOOP_CONTROL = "Loop Control"

class BaseStepDialog(QDialog):
    def __init__(self, parent=None, params=None):
        super().__init__(parent)
        self.params = params or {}
        self.setWindowTitle("Configure Step")
        self.setModal(True)
        # Apply dark theme
        self.apply_dark_theme()
        self.setup_ui()

    def apply_dark_theme(self):
        """Apply dark theme to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QSpinBox, QComboBox, QTextEdit {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
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
            QPushButton[text="Browse"] {
                background-color: #2d5f8b;
                min-width: 60px;
            }
            QPushButton[text="Browse"]:hover {
                background-color: #366ea3;
            }
            QPushButton[text="Browse"]:pressed {
                background-color: #255279;
            }
            QCheckBox, QRadioButton {
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 0.5em;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)

    def create_browse_button(self, text="Browse"):
        """Create a styled browse button"""
        button = QPushButton(text)
        button.setToolTip("Browse for file")
        button.setCursor(Qt.CursorShape.PointingHandCursor)  # Change cursor on hover
        return button

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Common fields for all steps
        self.name_edit = QLineEdit(self.params.get("name", ""))
        layout.addWidget(QLabel("Step Name:"))
        layout.addWidget(self.name_edit)

        # Loop control checkbox
        self.enable_loop = QCheckBox("Include in workflow loop")
        self.enable_loop.setChecked(self.params.get("enable_loop", True))  # Default to True
        self.enable_loop.setToolTip("When unchecked, this step will only be executed once, regardless of loop count")
        layout.addWidget(self.enable_loop)

        # Add specific fields
        self.add_specific_fields(layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def add_specific_fields(self, layout):
        pass

    def get_params(self):
        return {
            "name": self.name_edit.text(),
            "enable_loop": self.enable_loop.isChecked()
        }

class MouseClickDialog(BaseStepDialog):
    def add_specific_fields(self, layout):
        # Create all UI elements first
        # Coordinates input
        self.coord_widget = QWidget()  # Changed to instance variable
        coord_layout = QHBoxLayout()
        coord_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        self.x_coord = QSpinBox()
        self.y_coord = QSpinBox()
        self.x_coord.setRange(-9999, 9999)
        self.y_coord.setRange(-9999, 9999)
        # Set initial coordinates from params
        self.x_coord.setValue(self.params.get("x", 0))
        self.y_coord.setValue(self.params.get("y", 0))
        coord_layout.addWidget(QLabel("X:"))
        coord_layout.addWidget(self.x_coord)
        coord_layout.addWidget(QLabel("Y:"))
        coord_layout.addWidget(self.y_coord)
        self.coord_widget.setLayout(coord_layout)

        # Click type
        click_group = QGroupBox("Click Type")
        click_layout = QVBoxLayout()
        click_layout.setSpacing(5)  # Reduce spacing between radio buttons
        
        self.click_type = QButtonGroup()
        coord_radio = QRadioButton("Click at Coordinates")
        image_radio = QRadioButton("Click on Image")
        self.click_type.addButton(coord_radio, 0)
        self.click_type.addButton(image_radio, 1)
        
        # Set initial click type from params
        if self.params.get("click_type") == "image":
            image_radio.setChecked(True)
        else:
            coord_radio.setChecked(True)
        
        click_layout.addWidget(coord_radio)
        click_layout.addWidget(image_radio)
        click_group.setLayout(click_layout)

        # Mouse button selection
        button_group = QGroupBox("Mouse Button")
        button_layout = QVBoxLayout()
        button_layout.setSpacing(5)  # Reduce spacing between radio buttons
        self.mouse_button = QButtonGroup()
        left_radio = QRadioButton("Left Click")
        right_radio = QRadioButton("Right Click")
        self.mouse_button.addButton(left_radio, 0)
        self.mouse_button.addButton(right_radio, 1)
        
        # Set initial button type from params
        if self.params.get("button") == "right":
            right_radio.setChecked(True)
        else:
            left_radio.setChecked(True)
        
        button_layout.addWidget(left_radio)
        button_layout.addWidget(right_radio)
        button_group.setLayout(button_layout)

        # Image selection
        self.image_group = QGroupBox("Image Selection")
        image_layout = QVBoxLayout()
        image_layout.setSpacing(5)  # Reduce spacing between elements

        # Input type selection for images
        input_type_layout = QHBoxLayout()
        input_type_layout.setSpacing(10)  # Adjust spacing between radio buttons
        self.image_input_type = QButtonGroup()
        single_radio = QRadioButton("Single Image")
        multiple_radio = QRadioButton("Multiple Images")
        self.image_input_type.addButton(single_radio, 0)
        self.image_input_type.addButton(multiple_radio, 1)
        
        # Set initial input type from params
        if self.params.get("input_type") == "multiple":
            multiple_radio.setChecked(True)
        else:
            single_radio.setChecked(True)
        
        input_type_layout.addWidget(single_radio)
        input_type_layout.addWidget(multiple_radio)
        image_layout.addLayout(input_type_layout)

        # Single image selection
        self.single_image_widget = QWidget()
        single_image_layout = QHBoxLayout()
        single_image_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        self.image_path = QLineEdit()
        self.image_path.setText(self.params.get("image_path", ""))
        browse_btn = self.create_browse_button("Browse")
        browse_btn.clicked.connect(self.browse_single_image)
        single_image_layout.addWidget(self.image_path)
        single_image_layout.addWidget(browse_btn)
        self.single_image_widget.setLayout(single_image_layout)
        image_layout.addWidget(self.single_image_widget)

        # Multiple images selection
        self.multiple_images_widget = QWidget()
        multiple_images_layout = QVBoxLayout()
        multiple_images_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        multiple_images_layout.setSpacing(5)  # Reduce spacing
        
        # List widget for multiple images
        self.image_list = QListWidget()
        if self.params.get("image_list"):
            self.image_list.addItems(self.params["image_list"])
        multiple_images_layout.addWidget(self.image_list)
        
        # Add/Remove buttons for image list
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)  # Reduce spacing between buttons
        add_image_btn = QPushButton("Add Image")
        remove_image_btn = QPushButton("Remove Selected")
        add_image_btn.clicked.connect(self.add_image)
        remove_image_btn.clicked.connect(self.remove_image)
        buttons_layout.addWidget(add_image_btn)
        buttons_layout.addWidget(remove_image_btn)
        multiple_images_layout.addLayout(buttons_layout)
        
        self.multiple_images_widget.setLayout(multiple_images_layout)
        image_layout.addWidget(self.multiple_images_widget)

        self.image_group.setLayout(image_layout)

        # Now add all elements to the main layout in the correct order
        layout.addWidget(click_group)
        layout.addWidget(button_group)
        layout.addWidget(self.coord_widget)
        layout.addWidget(self.image_group)

        # Connect signals after all UI elements are created
        self.click_type.buttonClicked.connect(self.on_click_type_changed)
        self.image_input_type.buttonClicked.connect(self.on_image_input_type_changed)

        # Initial visibility based on current settings
        self.on_click_type_changed()
        self.on_image_input_type_changed()

        # Duration control
        duration_layout = QHBoxLayout()
        self.duration = QSpinBox()
        self.duration.setRange(0, 10)  # 0-10 seconds
        self.duration.setValue(self.params.get("duration", 1))  # Default 1 second
        self.duration.setSingleStep(1)
        duration_layout.addWidget(QLabel("Mouse Movement Duration (seconds):"))
        duration_layout.addWidget(self.duration)
        layout.addLayout(duration_layout)

        # Confidence threshold
        conf_layout = QHBoxLayout()
        self.confidence = QSpinBox()
        self.confidence.setRange(1, 100)
        conf_value = int(self.params.get("confidence", 0.9) * 100)
        self.confidence.setValue(conf_value)
        conf_layout.addWidget(QLabel("Confidence Threshold (%):"))
        conf_layout.addWidget(self.confidence)
        layout.addLayout(conf_layout)

        # Text input after click option
        text_group = QGroupBox("Text Input After Click")
        text_layout = QVBoxLayout()
        
        self.enable_text = QCheckBox("Type text after clicking")
        self.enable_text.setChecked(self.params.get("type_after_click", False))
        text_layout.addWidget(self.enable_text)
        
        # Container for all text input options
        self.text_options_widget = QWidget()
        text_options_layout = QVBoxLayout()
        text_options_layout.setContentsMargins(0, 0, 0, 0)
        
        # Text input type selection in its own group box
        input_type_group = QGroupBox("Input Type")
        input_type_layout = QVBoxLayout()
        
        self.text_input_type = QButtonGroup()
        fixed_radio = QRadioButton("Fixed Text")
        prompt_radio = QRadioButton("Prompt for Input")
        self.text_input_type.addButton(fixed_radio, 0)
        self.text_input_type.addButton(prompt_radio, 1)
        
        # Set initial text input type from params
        if self.params.get("text_input_type") == "prompt":
            prompt_radio.setChecked(True)
        else:
            fixed_radio.setChecked(True)
            
        input_type_layout.addWidget(fixed_radio)
        input_type_layout.addWidget(prompt_radio)
        input_type_group.setLayout(input_type_layout)
        text_options_layout.addWidget(input_type_group)
        
        # Text input field
        self.text_input_widget = QWidget()
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("Text to type:"))
        self.text_input = QLineEdit()
        self.text_input.setText(self.params.get("text_to_type", ""))
        self.text_input.setPlaceholderText("Enter text to type after click")
        text_input_layout.addWidget(self.text_input)
        self.text_input_widget.setLayout(text_input_layout)
        text_options_layout.addWidget(self.text_input_widget)
        
        # Prompt message field
        self.prompt_widget = QWidget()
        prompt_layout = QHBoxLayout()
        prompt_layout.addWidget(QLabel("Prompt Message:"))
        self.prompt_message = QLineEdit()
        self.prompt_message.setText(self.params.get("prompt_message", "Please enter the text:"))
        self.prompt_message.setPlaceholderText("Message to show when asking for input")
        prompt_layout.addWidget(self.prompt_message)
        self.prompt_widget.setLayout(prompt_layout)
        text_options_layout.addWidget(self.prompt_widget)
        
        # Delay before typing
        delay_layout = QHBoxLayout()
        self.type_delay = QSpinBox()
        self.type_delay.setRange(0, 10)  # 0-10 seconds
        self.type_delay.setValue(self.params.get("type_delay", 1))  # Default 1 second
        delay_layout.addWidget(QLabel("Delay before typing (seconds):"))
        delay_layout.addWidget(self.type_delay)
        text_options_layout.addLayout(delay_layout)
        
        # Special key after typing
        special_layout = QHBoxLayout()
        special_layout.addWidget(QLabel("Press key after typing:"))
        self.special_key = QComboBox()
        self.special_key.addItems(["None", "Enter", "Tab", "Space"])
        initial_key = self.params.get("special_key", "None")
        index = self.special_key.findText(initial_key)
        self.special_key.setCurrentIndex(index if index >= 0 else 0)
        special_layout.addWidget(self.special_key)
        text_options_layout.addLayout(special_layout)
        
        # Add all text options to the container widget
        self.text_options_widget.setLayout(text_options_layout)
        text_layout.addWidget(self.text_options_widget)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)

        # Connect signals
        self.enable_text.toggled.connect(self.on_text_enabled_changed)
        self.text_input_type.buttonClicked.connect(self.on_text_type_changed)
        
        # Set initial states
        self.text_options_widget.setVisible(self.enable_text.isChecked())
        self.on_text_type_changed()

    def on_click_type_changed(self):
        """Handle click type radio button changes"""
        is_image = self.click_type.checkedId() == 1
        self.image_group.setVisible(is_image)
        self.coord_widget.setVisible(not is_image)
        
        # Adjust dialog size when switching modes
        if is_image:
            self.coord_widget.setMaximumHeight(0)
        else:
            self.coord_widget.setMaximumHeight(16777215)  # Default max height
        
        # Force layout update
        self.adjustSize()

    def on_image_input_type_changed(self):
        """Handle image input type radio button changes"""
        is_multiple = self.image_input_type.checkedId() == 1
        self.single_image_widget.setVisible(not is_multiple)
        self.multiple_images_widget.setVisible(is_multiple)

    def browse_single_image(self):
        """Browse for a single image file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_name:
            self.image_path.setText(file_name)

    def add_image(self):
        """Add a new image to the list"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_name:
            self.image_list.addItem(file_name)

    def remove_image(self):
        """Remove the selected image from the list"""
        current_item = self.image_list.currentItem()
        if current_item:
            self.image_list.takeItem(self.image_list.row(current_item))

    def on_text_enabled_changed(self, enabled):
        """Handle text input enable/disable"""
        self.text_options_widget.setVisible(enabled)
        self.text_input.setEnabled(enabled)
        self.type_delay.setEnabled(enabled)
        self.special_key.setEnabled(enabled)
        self.prompt_message.setEnabled(enabled)
        for button in self.text_input_type.buttons():
            button.setEnabled(enabled)
        self.on_text_type_changed()  # Update field visibility

    def on_text_type_changed(self):
        """Handle text input type changes"""
        is_prompt = self.text_input_type.checkedId() == 1 and self.enable_text.isChecked()
        self.text_input.setVisible(not is_prompt)
        self.text_input.parentWidget().setVisible(not is_prompt)  # Hide the label too
        self.prompt_message.setVisible(is_prompt)
        self.prompt_message.parentWidget().setVisible(is_prompt)  # Show/hide the label too

    def get_params(self):
        params = super().get_params()
        is_image = self.click_type.checkedId() == 1
        is_multiple = self.image_input_type.checkedId() == 1

        params.update({
            "click_type": "image" if is_image else "coordinates",
            "button": "right" if self.mouse_button.checkedId() == 1 else "left",
            "x": self.x_coord.value(),
            "y": self.y_coord.value(),
            "duration": self.duration.value(),
            "confidence": self.confidence.value() / 100,
            "type_after_click": self.enable_text.isChecked(),
            "text_input_type": "prompt" if self.text_input_type.checkedId() == 1 else "fixed",
            "text_to_type": self.text_input.text() if self.enable_text.isChecked() and self.text_input_type.checkedId() == 0 else "",
            "prompt_message": self.prompt_message.text() if self.enable_text.isChecked() and self.text_input_type.checkedId() == 1 else "",
            "type_delay": self.type_delay.value(),
            "special_key": self.special_key.currentText() if self.special_key.currentText() != "None" else None,
        })

        if is_image:
            params.update({
                "input_type": "multiple" if is_multiple else "single",
                "image_path": self.image_path.text() if not is_multiple else "",
                "image_list": [self.image_list.item(i).text() 
                             for i in range(self.image_list.count())] if is_multiple else [],
                "current_image_index": 0  # Initialize index for multiple images
            })

        return params

class KeyboardTypeDialog(BaseStepDialog):
    def add_specific_fields(self, layout):
        # Input type selection
        input_type_group = QGroupBox("Input Type")
        input_type_layout = QVBoxLayout()
        self.input_type = QButtonGroup()
        single_radio = QRadioButton("Single Text Input")
        multiple_radio = QRadioButton("Multiple Text Inputs")
        self.input_type.addButton(single_radio, 0)
        self.input_type.addButton(multiple_radio, 1)
        
        # Set initial input type from params
        if self.params.get("input_type") == "multiple":
            multiple_radio.setChecked(True)
        else:
            single_radio.setChecked(True)
        
        input_type_layout.addWidget(single_radio)
        input_type_layout.addWidget(multiple_radio)
        input_type_group.setLayout(input_type_layout)
        layout.addWidget(input_type_group)

        # Single text input
        self.single_input_group = QGroupBox("Single Text Input")
        single_layout = QVBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setText(self.params.get("text", ""))
        single_layout.addWidget(self.text_input)
        self.single_input_group.setLayout(single_layout)
        layout.addWidget(self.single_input_group)

        # Multiple text inputs
        self.multiple_input_group = QGroupBox("Multiple Text Inputs")
        multiple_layout = QVBoxLayout()
        
        # List widget for multiple inputs
        self.text_list = QListWidget()
        if self.params.get("text_list"):
            self.text_list.addItems(self.params["text_list"])
        multiple_layout.addWidget(self.text_list)
        
        # Add/Remove buttons for list
        buttons_layout = QHBoxLayout()
        add_text_btn = QPushButton("Add Text")
        remove_text_btn = QPushButton("Remove Selected")
        add_text_btn.clicked.connect(self.add_text_item)
        remove_text_btn.clicked.connect(self.remove_text_item)
        buttons_layout.addWidget(add_text_btn)
        buttons_layout.addWidget(remove_text_btn)
        multiple_layout.addLayout(buttons_layout)
        
        self.multiple_input_group.setLayout(multiple_layout)
        layout.addWidget(self.multiple_input_group)

        # Special keys
        special_group = QGroupBox("Special Key (Optional)")
        special_layout = QVBoxLayout()
        self.special_keys = QComboBox()
        special_keys = [
            "None", "Enter", "Tab", "Space", "Backspace", 
            "Delete", "Escape", "Up", "Down", "Left", "Right"
        ]
        self.special_keys.addItems(special_keys)
        initial_key = self.params.get("special_key", "None")
        index = self.special_keys.findText(initial_key)
        if index >= 0:
            self.special_keys.setCurrentIndex(index)
        special_layout.addWidget(self.special_keys)
        special_group.setLayout(special_layout)
        layout.addWidget(special_group)

        # Delay
        delay_layout = QHBoxLayout()
        self.delay = QSpinBox()
        self.delay.setRange(0, 10)  # 0-10 seconds
        self.delay.setValue(self.params.get("delay", 1))  # Default 1 second
        delay_layout.addWidget(QLabel("Delay between keystrokes (seconds):"))
        delay_layout.addWidget(self.delay)
        layout.addLayout(delay_layout)

        # Connect input type radio buttons to toggle visibility
        self.input_type.buttonClicked.connect(self.toggle_input_type)
        self.toggle_input_type()

    def toggle_input_type(self):
        """Toggle visibility of input type groups based on selection"""
        is_single = self.input_type.checkedId() == 0
        self.single_input_group.setVisible(is_single)
        self.multiple_input_group.setVisible(not is_single)

    def add_text_item(self):
        """Add a new text item to the list"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Text")
        layout = QVBoxLayout(dialog)
        
        text_edit = QLineEdit()
        layout.addWidget(QLabel("Enter Text:"))
        layout.addWidget(text_edit)
        
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted and text_edit.text():
            self.text_list.addItem(text_edit.text())

    def remove_text_item(self):
        """Remove the selected text item from the list"""
        current_item = self.text_list.currentItem()
        if current_item:
            self.text_list.takeItem(self.text_list.row(current_item))

    def get_params(self):
        params = super().get_params()
        is_single = self.input_type.checkedId() == 0
        
        params.update({
            "input_type": "single" if is_single else "multiple",
            "text": self.text_input.text() if is_single else "",
            "text_list": [self.text_list.item(i).text() 
                         for i in range(self.text_list.count())] if not is_single else [],
            "special_key": self.special_keys.currentText() if self.special_keys.currentText() != "None" else None,
            "delay": self.delay.value(),
            "current_text_index": 0  # Track which text to use in multiple mode
        })
        return params

class WaitDialog(BaseStepDialog):
    def add_specific_fields(self, layout):
        # Wait duration
        duration_layout = QHBoxLayout()
        self.duration = QSpinBox()
        self.duration.setRange(0, 3600)  # 0 to 3600 seconds
        _saved = int(self.params.get("duration", 1))
        self.duration.setValue(_saved)
        duration_layout.addWidget(QLabel("Duration (seconds):"))
        duration_layout.addWidget(self.duration)
        layout.addLayout(duration_layout)

    def get_params(self):
        params = super().get_params()
        params.update({
            "duration": self.duration.value()
        })
        return params


class WaitForImageDialog(BaseStepDialog):
    """Wait until a reference image appears on screen (or disappear variant)."""

    def __init__(self, parent=None, params=None, disappear=False):
        self._disappear = disappear
        super().__init__(parent, params)

    def setup_ui(self):
        super().setup_ui()
        self.setWindowTitle(
            "Wait for Image to Disappear" if self._disappear else "Wait for Image"
        )

    def add_specific_fields(self, layout):
        img_layout = QHBoxLayout()
        self.image_path = QLineEdit()
        self.image_path.setText(self.params.get("image_path", ""))
        browse_btn = self.create_browse_button("Browse")
        browse_btn.clicked.connect(self._browse_image)
        img_layout.addWidget(QLabel("Reference image:"))
        img_layout.addWidget(self.image_path)
        img_layout.addWidget(browse_btn)
        layout.addLayout(img_layout)

        conf_layout = QHBoxLayout()
        self.confidence = QSpinBox()
        self.confidence.setRange(1, 100)
        conf_value = int(self.params.get("confidence", 0.9) * 100)
        self.confidence.setValue(conf_value)
        conf_layout.addWidget(QLabel("Confidence threshold (%):"))
        conf_layout.addWidget(self.confidence)
        layout.addLayout(conf_layout)

        timeout_layout = QHBoxLayout()
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 3600)
        self.timeout.setValue(self.params.get("timeout", 30))
        timeout_layout.addWidget(QLabel("Timeout (seconds):"))
        timeout_layout.addWidget(self.timeout)
        layout.addLayout(timeout_layout)

    def _browse_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select reference image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_name:
            self.image_path.setText(file_name)

    def get_params(self):
        params = super().get_params()
        params.update({
            "image_path": self.image_path.text().strip(),
            "confidence": self.confidence.value() / 100,
            "timeout": self.timeout.value(),
        })
        return params


class WaitForImageDisappearDialog(WaitForImageDialog):
    def __init__(self, parent=None, params=None):
        super().__init__(parent, params, disappear=True)


class KeyboardSpecialDialog(BaseStepDialog):
    def add_specific_fields(self, layout):
        # Key selection
        key_group = QGroupBox("Key")
        key_layout = QVBoxLayout()
        self.key = QComboBox()
        
        # Gather all key options in categories
        special_keys = [
            "Enter", "Tab", "Space", "Backspace", "Delete", 
            "Escape", "Up", "Down", "Left", "Right"
        ]
        
        function_keys = [f"F{i}" for i in range(1, 13)]  # F1-F12
        
        alphabet_keys = [chr(ord('A') + i) for i in range(26)]  # A-Z
        
        number_keys = [str(i) for i in range(10)]  # 0-9
        
        symbol_keys = [
            "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/",
            "~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
            "_", "+", "{", "}", "|", ":", "\"", "<", ">", "?"
        ]
        
        # Add all keys to the dropdown with category headers
        self.key.addItem("--- Special Keys ---")
        self.key.addItems(special_keys)
        
        self.key.addItem("--- Function Keys ---")
        self.key.addItems(function_keys)
        
        self.key.addItem("--- Alphabet Keys ---")
        self.key.addItems(alphabet_keys)
        
        self.key.addItem("--- Number Keys ---")
        self.key.addItems(number_keys)
        
        self.key.addItem("--- Symbol Keys ---")
        self.key.addItems(symbol_keys)
        
        # Set initial key
        initial_key = self.params.get("key", "")
        # Find the index of the initial key if it exists
        for i in range(self.key.count()):
            if self.key.itemText(i) == initial_key:
                self.key.setCurrentIndex(i)
                break
        
        key_layout.addWidget(self.key)
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)

        # Modifiers
        modifier_group = QGroupBox("Modifiers")
        modifier_layout = QVBoxLayout()
        self.ctrl = QCheckBox("Ctrl")
        self.alt = QCheckBox("Alt")
        self.shift = QCheckBox("Shift")
        self.win = QCheckBox("Windows")
        # Set initial modifiers
        modifiers = self.params.get("modifiers", [])
        self.ctrl.setChecked("ctrl" in modifiers)
        self.alt.setChecked("alt" in modifiers)
        self.shift.setChecked("shift" in modifiers)
        self.win.setChecked("win" in modifiers)
        modifier_layout.addWidget(self.ctrl)
        modifier_layout.addWidget(self.alt)
        modifier_layout.addWidget(self.shift)
        modifier_layout.addWidget(self.win)
        modifier_group.setLayout(modifier_layout)
        layout.addWidget(modifier_group)
        
    def get_params(self):
        params = super().get_params()
        modifiers = []
        if self.ctrl.isChecked():
            modifiers.append("ctrl")
        if self.alt.isChecked():
            modifiers.append("alt")
        if self.shift.isChecked():
            modifiers.append("shift")
        if self.win.isChecked():
            modifiers.append("win")
        
        # Don't use separator items as keys
        key_text = self.key.currentText()
        if not key_text.startswith("---"):
            params.update({
                "key": key_text,
                "modifiers": modifiers
            })
        else:
            # If a separator is selected, default to first actual key
            for i in range(self.key.count()):
                item_text = self.key.itemText(i)
                if not item_text.startswith("---"):
                    params.update({
                        "key": item_text,
                        "modifiers": modifiers
                    })
                    break
        
        return params

class LoopControlDialog(BaseStepDialog):
    def setup_ui(self):
        super().setup_ui()
        
        layout = self.layout()
        
        # Loop control type
        self.control_type_group = QGroupBox("Loop Control Type")
        control_type_layout = QVBoxLayout()
        
        self.start_loop_radio = QRadioButton("Start Loop")
        self.end_loop_radio = QRadioButton("End Loop")
        
        control_type_layout.addWidget(self.start_loop_radio)
        control_type_layout.addWidget(self.end_loop_radio)
        
        # Set default based on params or default to Start Loop
        if self.params.get("control_type") == "end":
            self.end_loop_radio.setChecked(True)
        else:
            self.start_loop_radio.setChecked(True)
        
        self.control_type_group.setLayout(control_type_layout)
        layout.addWidget(self.control_type_group)
        
        # Loop ID (to match start and end loops)
        loop_id_layout = QHBoxLayout()
        loop_id_layout.addWidget(QLabel("Loop ID:"))
        self.loop_id = QSpinBox()
        self.loop_id.setRange(1, 999)
        self.loop_id.setValue(self.params.get("loop_id", 1))
        self.loop_id.setToolTip("Unique identifier for this loop (use same ID for start and end)")
        loop_id_layout.addWidget(self.loop_id)
        layout.addLayout(loop_id_layout)
        
        # Loop count (only relevant for start loop)
        self.loop_settings = QGroupBox("Loop Settings")
        loop_settings_layout = QVBoxLayout()
        
        loop_count_layout = QHBoxLayout()
        loop_count_layout.addWidget(QLabel("Loop Count:"))
        self.loop_count = QSpinBox()
        self.loop_count.setRange(1, 999)
        self.loop_count.setValue(self.params.get("loop_count", 1))
        self.loop_count.setToolTip("Number of times to execute the loop")
        loop_count_layout.addWidget(self.loop_count)
        loop_settings_layout.addLayout(loop_count_layout)
        
        self.loop_settings.setLayout(loop_settings_layout)
        layout.addWidget(self.loop_settings)
        
        # Enable/disable loop count based on control type
        self.start_loop_radio.toggled.connect(self.update_ui_state)
        self.update_ui_state()
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def update_ui_state(self):
        # Enable/disable loop count based on control type
        self.loop_settings.setEnabled(self.start_loop_radio.isChecked())
    
    def get_params(self):
        params = super().get_params()
        
        params.update({
            "control_type": "start" if self.start_loop_radio.isChecked() else "end",
            "loop_id": self.loop_id.value(),
            "loop_count": self.loop_count.value() if self.start_loop_radio.isChecked() else 1,
        })
        
        return params

STEP_DIALOGS = {
    StepType.MOUSE_CLICK: MouseClickDialog,
    StepType.KEYBOARD_TYPE: KeyboardTypeDialog,
    StepType.KEYBOARD_SPECIAL: KeyboardSpecialDialog,
    StepType.WAIT: WaitDialog,
    StepType.WAIT_FOR_IMAGE: WaitForImageDialog,
    StepType.WAIT_FOR_IMAGE_DISAPPEAR: WaitForImageDisappearDialog,
    StepType.LOOP_CONTROL: LoopControlDialog,
} 