import argparse
import tempfile
from os.path import abspath, dirname
from typing import List, Tuple, Optional
import logging
import sys

from gtts import gTTS
from loguru import logger
from moviepy import editor as mv
from moviepy.config import change_settings

# Configure loguru to replace MoviePy's default logger
def configure_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logging.basicConfig(level=logging.ERROR)
    moviepy_logger = logging.getLogger("moviepy")
    moviepy_logger.setLevel(logging.INFO)
    moviepy_logger.addHandler(logging.StreamHandler())

configure_logging()

class VideoMaker:
    ROOT_DIR = abspath(dirname(__file__))
    CHAR_DIR = f"{ROOT_DIR}\\character\\"
    STATICS_DIR = f"{ROOT_DIR}\\statics\\"

    SPRITES = {
        "anger": mv.ImageClip(f"{CHAR_DIR}anger.png"),
        "anger_screaming": mv.ImageClip(f"{CHAR_DIR}anger_screaming.png"),
        "fearful": mv.ImageClip(f"{CHAR_DIR}fearful.png"),
        "frown": mv.ImageClip(f"{CHAR_DIR}frown.png"),
        "greedy": mv.ImageClip(f"{CHAR_DIR}greedy.png"),
        "happy_screaming": mv.ImageClip(f"{CHAR_DIR}happy_screaming.png"),
        "happy": mv.ImageClip(f"{CHAR_DIR}happy.png"),
        "joy": mv.ImageClip(f"{CHAR_DIR}joy.png"),
        "mischief": mv.ImageClip(f"{CHAR_DIR}mischief.png"),
        "smile": mv.ImageClip(f"{CHAR_DIR}smile.png"),
        "speaking_low": mv.ImageClip(f"{CHAR_DIR}speaking_low.png"),
        "speaking_medium": mv.ImageClip(f"{CHAR_DIR}speaking_medium.png"),
        "worried": mv.ImageClip(f"{CHAR_DIR}worried.png"),
    }

    def __init__(self, script_path: str, output_path: Optional[str] = None):
        self.script_path = script_path
        self.output_path = output_path
        self.clips = []
        self.current_time = 0

    class InvalidScriptError(Exception):
        pass

    @staticmethod
    def remove_affix(text: str, affixes: Tuple[str]) -> str:
        for affix in affixes:
            text = text.replace(affix, "")
        return text

    @staticmethod
    def google_tts_to_clip(text: str, start_time: float, duration: float = None) -> Tuple[mv.VideoClip, float]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
            gTTS(text, lang='en').save(tmp_audio_file.name)
            audio_clip = mv.AudioFileClip(tmp_audio_file.name)
            audio_duration = audio_clip.duration

            if duration is None:
                duration = audio_duration
            elif audio_duration > duration:
                audio_clip = audio_clip.subclip(0, duration)

            video_clip = mv.ColorClip(size=(1, 1), color=(0, 0, 0)).set_duration(duration)
            return mv.CompositeVideoClip([video_clip.set_audio(audio_clip)]).set_start(start_time), duration

    @staticmethod
    def read_script(script_path: str) -> str:
        with open(script_path, "r", encoding="utf-8") as script_file:
            return script_file.read()

    @staticmethod
    def parse_start_command(script: str) -> int:
        if not script.splitlines()[0].lower().startswith("[start"):
            raise VideoMaker.InvalidScriptError("The first line of the script must be '[START]'.")
        else:
            try:
                return int(VideoMaker.remove_affix(script.splitlines()[0], ("[", "]")).split(" ")[1])
            except IndexError:
                raise VideoMaker.InvalidScriptError("Duration not defined in '[START]' command. Example: '[START 5]'")

    @staticmethod
    def create_initial_background_clip(duration: int) -> mv.ImageClip:
        return mv.ImageClip(f"{VideoMaker.STATICS_DIR}bg_white.png").set_duration(duration)

    def add_emotion_clip(self, emotion_name: str, duration: float) -> float:
        emotion_clip = VideoMaker.SPRITES[emotion_name].set_duration(duration)
        emotion_height = int(emotion_clip.h // 1.4)
        emotion_clip = emotion_clip.resize(height=emotion_height).set_position("bottom", "right").margin(bottom=10, opacity=0).margin(left=1500, opacity=0).set_start(self.current_time)
        self.clips.append(emotion_clip)
        self.current_time += duration
        return self.current_time

    def add_espeech_clip(self, emotion_name: str, text: str, duration: float = None) -> float:
        tts_clip, tts_duration = VideoMaker.google_tts_to_clip(text, self.current_time, duration)
        emotion_duration = duration if duration else tts_duration
        emotion_clip = VideoMaker.SPRITES[emotion_name].set_duration(emotion_duration)
        emotion_height = int(emotion_clip.h // 1.4)
        emotion_clip = emotion_clip.resize(height=emotion_height).set_position("bottom", "right").margin(bottom=10, opacity=0).margin(left=1500, opacity=0).set_start(self.current_time)
        self.clips.append(emotion_clip)
        self.clips.append(tts_clip)
        self.current_time += emotion_duration
        return self.current_time

    def add_textspeech_clip(self, text: str, duration: float = None) -> float:
        tts_clip, tts_duration = VideoMaker.google_tts_to_clip(text, self.current_time, duration)
        text_duration = duration if duration else tts_duration
        text_clip = mv.TextClip(text, fontsize=70, color='black', size=(1920, 1080), method='caption').set_duration(text_duration).set_position('center').crossfadein(0.5).crossfadeout(0.5).set_start(self.current_time).set_audio(tts_clip.audio)
        self.clips.append(text_clip)
        self.current_time += text_duration
        return self.current_time

    def add_insert_clip(self, video_path: str) -> float:
        insert_clip = mv.VideoFileClip(video_path).set_start(self.current_time)
        self.clips.append(insert_clip)
        self.current_time += insert_clip.duration
        return self.current_time

    def export_final_video(self, save_path: str, fps: int):
        try:
            final_video = mv.CompositeVideoClip(self.clips).write_videofile(save_path, fps=fps, threads=32, codec='libx264')
            logger.info(f"Final video '{save_path}' exported at {fps} FPS.")
        except OSError as e:
            if "unable to find a suitable output format" in str(e).lower():
                logger.error("Output format error: Invalid output file type. Try again with a different file type (e.g. .mp4).")
                exit(1)

    def process_script(self):
        script = VideoMaker.read_script(self.script_path)
        initial_duration = VideoMaker.parse_start_command(script)
        bg_clip = VideoMaker.create_initial_background_clip(initial_duration)
        self.clips.append(bg_clip)

        for line in script.splitlines():
            if line.lower().startswith("[end"):
                command = VideoMaker.remove_affix(line, ("[", "]")).split(" ")
                if not self.output_path:
                    self.output_path = abspath(command[1])
                fps = int(command[2])
                self.export_final_video(self.output_path, fps)
            elif line.lower().strip() == "":
                continue
            elif line.lower().startswith("[emotion"):
                command = VideoMaker.remove_affix(line, ("[", "]")).split(" ")
                emotion_name = command[1]
                duration = float(command[2])
                self.add_emotion_clip(emotion_name, duration)
            elif line.lower().startswith("[espeech"):
                command = VideoMaker.remove_affix(line, ("[", "]")).split(" ")
                emotion_name = command[1]
                if command[2] == "auto":
                    duration = None
                    text = " ".join(command[3:])
                else:
                    duration = float(command[2])
                    text = " ".join(command[3:])
                self.add_espeech_clip(emotion_name, text, duration)
            elif line.lower().startswith("[insert"):
                command = VideoMaker.remove_affix(line, ("[", "]")).split(" ")
                video_path = command[1]
                self.add_insert_clip(video_path)
            elif line.lower().startswith("[textspeech"):
                command = VideoMaker.remove_affix(line, ("[", "]")).split(" ")
                if command[1] == "auto":
                    duration = None
                    text = " ".join(command[2:])
                else:
                    duration = float(command[1])
                    text = " ".join(command[2:])
                self.add_textspeech_clip(text, duration)

def main():
    parser = argparse.ArgumentParser(description="Generate videos based on a script.")
    parser.add_argument("script_path", type=str, help="Path to the script file.")
    parser.add_argument("-o", "--output_path", type=str, help="Optional path to save the final video. If not provided, it will use the path in the [END] tag.")
    parser.add_argument("fps", type=int, help="Frames per second for the final video.")

    args = parser.parse_args()

    change_settings({"IMAGEMAGICK_BINARY": (VideoMaker.ROOT_DIR + "\\magick\\magick.exe")})
    video_maker = VideoMaker(args.script_path, args.output_path)
    video_maker.process_script()

if __name__ == '__main__':
    main()
