# Hand-Eye Coordination Controller

A real-time hand-eye coordination control system that integrates eye tracking and hand gesture recognition for multi-stage control operations.

## 🎯 Features

- **Three-Stage Control Logic**: Target selection → Action control → Output generation
- **Eye Tracking**: Real-time eye movement and blink detection
- **Hand Gesture Recognition**: Data glove integration with 6 gesture types
- **Automatic State Transitions**: Seamless flow between control stages
- **Signal Quality Control**: Noise filtering and duplicate signal prevention
- **Multiple Control Sequences**: Support for both 2-signal and 4-signal sequences

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- OpenCV
- PySerial
- NumPy
- Data glove hardware (for hand gesture recognition)
- Webcam (for eye tracking)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hand-eye-coordination-controller.git
cd hand-eye-coordination-controller
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the system:
```bash
python main.py
```

## 📋 Control Sequences

### Standard Control Sequences (2 signals)

| Eye Signals | Target |
|-------------|--------|
| LEFT + LEFT_EYE_CLOSED | 1 |
| RIGHT + RIGHT_EYE_CLOSED | 2 |
| LEFT + RIGHT_EYE_CLOSED | 3 |
| RIGHT + LEFT_EYE_CLOSED | 4 |

### Special Control Sequence (4 signals)

| Eye Signals | Target |
|-------------|--------|
| LEFT + RIGHT + LEFT_EYE_CLOSED + RIGHT_EYE_CLOSED | 5 |

### Hand Gestures

| Gesture | Description |
|---------|-------------|
| FIST | Closed fist |
| FIVE | Open hand with all fingers extended |
| GOOD | Thumbs up |
| ROCK | Rock and roll gesture (index and pinky extended) |
| GUN | Gun gesture (thumb, index, middle extended) |
| F_CK | Middle finger gesture |

## 🔄 Control Flow

### Stage 1: Target Selection
- Use eye signals to select control targets (1-5)
- Support both 2-signal and 4-signal sequences
- UP signal resets to stage 1

### Stage 2: Action Control
- Use hand gestures to specify control actions
- Only hand signals are processed in this stage
- Eye signals are ignored

### Stage 3: Output Generation
- Automatic generation of final control command
- Format: `"Target Action"` (e.g., `"1 FIST"`, `"5 GOOD"`)
- Auto-return to stage 1 for continuous operation

## 📊 Example Output

```
=== 启动手眼协同控制系统 ===
进入阶段1
LEFT
RIGHT
LEFT_EYE_CLOSED
RIGHT_EYE_CLOSED
进入阶段2
FIST
进入阶段3
最终输出为：5 FIST
进入阶段1
```

## 🛠️ Configuration

### Camera Settings
```bash
python main.py --camera 1
```

### Serial Port Settings
```bash
python main.py --hand-port COM6
```

### Test Mode
```bash
python main.py --test
```

## 📁 Project Structure

```
hand-eye-coordination-controller/
├── main.py                 # Main application entry point
├── coordinator.py          # Core coordination logic
├── eye_interface.py        # Eye tracking interface
├── hand_interface.py       # Hand gesture interface
├── video_input.py          # Video capture module
├── gaze_model.py           # Eye tracking model
├── controller.py           # Eye control controller
├── gesture_recognizer.py  # Hand gesture recognition
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── control_logic.txt     # Control logic documentation
```

## 🔧 Hardware Requirements

### Eye Tracking
- USB webcam
- Good lighting conditions
- Face visibility

### Hand Gesture Recognition
- Data glove with serial output
- COM port connection (Windows) or /dev/ttyUSB* (Linux)
- Calibration data (max_list/min_list)

## 📝 API Reference

### HandEyeCoordinator

Main coordination controller class.

```python
from coordinator import HandEyeCoordinator

coordinator = HandEyeCoordinator()
coordinator.set_output_callback(output_handler)
coordinator.process_eye_signal("LEFT")
coordinator.process_hand_signal("FIST")
```

### EyeSignalInterface

Eye tracking signal interface.

```python
from eye_interface import EyeSignalInterface

eye_interface = EyeSignalInterface(camera_index=1)
eye_interface.set_signal_callback(signal_handler)
eye_interface.start()
```

### HandSignalInterface

Hand gesture signal interface.

```python
from hand_interface import HandSignalInterface

hand_interface = HandSignalInterface(port='COM6')
hand_interface.set_signal_callback(signal_handler)
hand_interface.start()
```

## 🐛 Troubleshooting

### Common Issues

1. **Camera not detected**
   - Check camera permissions
   - Try different camera indices
   - Ensure camera is not used by other applications

2. **Serial port connection failed**
   - Verify COM port number
   - Check data glove connection
   - Ensure proper drivers are installed

3. **Calibration not completing**
   - Wait for data glove to send calibration data
   - Check serial communication
   - Verify data glove is functioning properly

### Debug Mode

Run with test mode for debugging:
```bash
python main.py --test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **[110]** - *Initial work* - [YourGitHub](https://github.com/yourusername)

## 🙏 Acknowledgments

- OpenCV community for computer vision tools
- PySerial for serial communication
- Data glove hardware manufacturers
- Eye tracking research community

## 📚 References

- [OpenCV Documentation](https://docs.opencv.org/)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
- [Eye Tracking Research](https://en.wikipedia.org/wiki/Eye_tracking)
- [Hand Gesture Recognition](https://en.wikipedia.org/wiki/Gesture_recognition)