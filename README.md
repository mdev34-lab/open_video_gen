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

1. Create a script file (e.g., `script.xml`) using the custom formatting:

```
<video resolution="1080x1920">
    <background color="lightgrey"/>
    <emotion name="happy" duration="2"/>
    <espeech emotion="speaking_low" duration="auto">Hmm, let me think about that.</espeech>
    <textspeech duration="5">This is some text that will wrap.</textspeech>
    <emotion name="joy" duration="3"/>
    <end output="my_video.mp4" fps="30"/>
</video>
```

2. Run the OpenVideoGen script:

```
python openvideogen.py script.xml
```

3. The generated video will be saved in the output directory specified in your script file.

## Script Tags

- `<video resolution="1920x1080">`: Root tag for the script file. Resolution may be specified (optional). Must be closed.
- `<insert path="path/to/video.mp4"/>`: Insert the specified sub-video into the video (not tested)
- `<emotion name="happy" duration="2"/>`: Displays the specified sprite for the specified duration.
- `<espeech emotion="happy" duration="auto">`: Applies TTS with specified sprite with specified duration (default "auto" or an integer). Must be closed.
- `<textspeech duration="5">`: Applies TTS while showing text on the screen. Duration is "auto" (default) or an integer. Must be closed.
- `<end output="my_video.mp4" fps="30"/>`: Ends the video, specifying output filename and FPS (both mandatory)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- Thanks to all contributors who have helped with the development of OpenVideoGen.
- Special thanks to the open-source community for providing valuable tools and libraries used in this project.
