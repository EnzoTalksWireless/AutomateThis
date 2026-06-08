# Automation 4.0 ![Automation 4.0 Logo](icon.png)



## 🚀 Overview

**Automation 4.0** is a sophisticated, high-performance desktop automation suite designed to streamline complex workflows through intelligent robotic process automation (RPA). Built with a focus on precision and reliability, it enables users to automate repetitive manual tasks across any desktop application without the need for complex scripting.


---

## ✨ Key Features

### 🖼️ Computer Vision & OCR
Leverage the power of **OpenCV** and **Tesseract OCR** to interact with elements that don't have standard UI hooks. 
- **Image-Based Triggering**: Click and interact based on visual patterns on the screen.
- **Dynamic Recognition**: Adaptive confidence levels for reliable image matching.

### ⌨️ Advanced Macro Engine
Total control over system inputs with sub-millisecond precision.
- **Mouse Orchestration**: Absolute/Relative coordinates, smooth movement, and multi-click behaviors.
- **Keyboard Mastery**: Full support for international character sets, modifier keys (Ctrl, Alt, Shift), and function keys.

### 🔄 Intelligent Workflow Logic
Build complex execution paths with ease.
- **Nested Looping**: Support for multi-level loops to handle iterative data processing.
- **Wait States**: Intelligent pauses to sincronize with application response times.
- **Undo/Redo System**: Seamlessly iterate on your automation steps during the design phase.

### 🛠️ Professional Tooling
- **Real-Time Recorder**: Capture actions as you perform them for rapid prototype building.
- **Coordinate Inspector**: Precision tool for mapping exact screen positions.
- **Execution Analytics**: Detailed logs and real-time debug console for deep troubleshooting.

---

## 🛠️ Technology Stack

- **Core Engine**: Python 3.x
- **GUI Framework**: PyQt6 (High DPI Support)
- **Vision Engine**: OpenCV & Pillow
- **Automation Layer**: PyAutoGUI, Keyboard, & Mouse
- **OCR Engine**: Tesseract OCR
- **System Integration**: PyWin32 (Windows Optimized)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Tesseract OCR (Optional but recommended, for OCR features)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/EnzoTalksWireless/AutomateThis.git
   cd AutomateThis
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the application:
   ```bash
   python automate.py
   ```

---

## 📖 Feature Guide

### 1. Visual Click
Interacts with elements based on coordinates or image patterns.
```yaml
Type: Mouse Click
Mode: Coordinates / Image Match
Properties: X, Y, Confidence, Image Path
```

### 2. Smart Input
Automates text entry with adjustable delays to mimic human behavior.
```yaml
Type: Keyboard Type
Properties: String, Character Delay, Post-Action Key (e.g., Enter)
```

### 3. Logic Gates & Loops
Orchestrate the flow of your automation.
```yaml
- START LOOP (ID: 1, Iterations: 10)
    - Action 1
    - ACTION 2
- END LOOP (ID: 1)
```

<p align="center">
  Built with ❤️ for productivity.
</p>
