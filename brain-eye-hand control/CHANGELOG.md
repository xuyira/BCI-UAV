# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

### Added
- Initial release of Hand-Eye Coordination Controller
- Three-stage control logic implementation
- Eye tracking with blink detection support
- Hand gesture recognition via data glove
- Support for 5 different control targets (1-5)
- Standard 2-signal control sequences
- Special 4-signal control sequence (LEFT + RIGHT + LEFT_EYE_CLOSED + RIGHT_EYE_CLOSED = Target 5)
- Automatic state transitions between control stages
- Signal quality control and noise filtering
- Real-time serial communication for data glove
- Camera integration for eye tracking
- Comprehensive error handling and logging
- Command-line interface with configuration options
- Test mode for debugging and development

### Features
- **Eye Tracking**: Real-time eye movement and individual eye blink detection
- **Hand Gesture Recognition**: Support for 6 different hand gestures (FIST, FIVE, GOOD, ROCK, GUN, F_CK)
- **Multi-Stage Control**: Seamless flow between target selection, action control, and output generation
- **Signal Quality Control**: Automatic filtering of duplicate signals and invalid inputs
- **Hardware Integration**: Support for USB cameras and serial data glove communication
- **Cross-Platform**: Compatible with Windows, Linux, and macOS

### Technical Details
- Python 3.7+ compatibility
- OpenCV for computer vision
- PySerial for hardware communication
- NumPy for numerical computations
- Thread-safe signal processing
- Modular architecture for easy extension

### Documentation
- Comprehensive README with usage examples
- API reference documentation
- Hardware setup instructions
- Troubleshooting guide
- MIT License

## [Unreleased]

### Planned Features
- GUI interface for easier configuration
- Additional hand gesture support
- Machine learning-based gesture recognition
- Multi-camera support
- Network communication for remote control
- Data logging and analysis tools
- Performance optimization
- Unit test coverage
- CI/CD pipeline setup
