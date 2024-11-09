# OpenVideoGen

OpenVideoGen is an automated video generation tool built with Python 3.11. This project allows users to create videos from custom-formatted scripts, processing them into fully rendered video outputs.

## Features

- Automated video generation from text scripts
- Custom scripting language for video creation
- Support for emotions and speech styles
- Integration of user-provided assets (e.g., scanned sketches)
- Flexible timing and duration controls

## Requirements

- Python 3.11
- Windows 10 or Windows 11

## Installation

To install OpenVideoGen, clone this repository and install the required dependencies:

```
git clone <url>
cd OpenVideoGen
pip install -r requirements.txt
```

## Usage

1. Create a script file (e.g., `script.txt`) using the custom formatting:

```
[START 60]
[EMOTION speaking_low 0.5]
[ESPEECH happy auto] Hello! This is a completely automated video i made using Python.
[TEXTSPEECH auto] In my current workflow, i write a script and it gets processed into a video.
[TEXTSPEECH auto] The script has custom formatting and commands, like ESPEECH, START or END.
[ESPEECH happy_screaming auto] I hope you like it! For the assets i used my own scanned sketches.
[ESPEECH speaking_low auto] But the script isn't perfect. For now, it's just a proof of concept.
[TEXTSPEECH auto] But nevertheless, pretty cool! Goodbye!
[END video.mp4 12]
```

2. Run the OpenVideoGen script:

```
python openvideogen.py script.txt
```

3. The generated video will be saved as `video.mp4` in the output directory.

## Script Commands

- `[START duration]`: Begins the video with specified duration in seconds
- `[EMOTION type intensity]`: Sets the emotion for the following lines
- `[ESPEECH style auto]`: Applies emotional speech with specified style
- `[TEXTSPEECH auto]`: Converts text to speech
- `[END filename duration]`: Ends the video, specifying output filename and duration

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- Thanks to all contributors who have helped with the development of OpenVideoGen.
- Special thanks to the open-source community for providing valuable tools and libraries used in this project.
