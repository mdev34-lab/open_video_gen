#!/usr/bin/env python3

import argparse
import tempfile
from os.path import abspath, dirname
import os  # Ensure os is imported for os.path.join
from typing import List, Tuple, Optional
import logging
import sys
import numpy as np
import re

from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm
from gtts import gTTS
from loguru import logger
from moviepy import editor as mv
from moviepy.config import change_settings
import cv2 as cv # Keep this to force people to install opencv-python

# The star of the show: VideoMaker class.
class VideoMaker:
    ROOT_DIR = abspath(dirname(__file__))
    CHAR_DIR = os.path.join(ROOT_DIR, "character")  # Correct usage of os.path.join
    STATICS_DIR = os.path.join(ROOT_DIR, "statics")  # Correct usage of os.path.join

    # Sprite cache.
    SPRITES = {
        "anger": mv.ImageClip(os.path.join(CHAR_DIR, "anger.png")),  # Correct usage of os.path.join
        "anger_screaming": mv.ImageClip(os.path.join(CHAR_DIR, "anger_screaming.png")),  # Correct usage of os.path.join
        "fearful": mv.ImageClip(os.path.join(CHAR_DIR, "fearful.png")),  # Correct usage of os.path.join
        "frown": mv.ImageClip(os.path.join(CHAR_DIR, "frown.png")),  # Correct usage of os.path.join
        "greedy": mv.ImageClip(os.path.join(CHAR_DIR, "greedy.png")),  # Correct usage of os.path.join
        "happy_screaming": mv.ImageClip(os.path.join(CHAR_DIR, "happy_screaming.png")),  # Correct usage of os.path.join
        "happy": mv.ImageClip(os.path.join(CHAR_DIR, "happy.png")),  # Correct usage of os.path.join
        "joy": mv.ImageClip(os.path.join(CHAR_DIR, "joy.png")),  # Correct usage of os.path.join
        "mischief": mv.ImageClip(os.path.join(CHAR_DIR, "mischief.png")),  # Correct usage of os.path.join
        "smile": mv.ImageClip(os.path.join(CHAR_DIR, "smile.png")),  # Correct usage of os.path.join
        "speaking_low": mv.ImageClip(os.path.join(CHAR_DIR, "speaking_low.png")),  # Correct usage of os.path.join
        "speaking_medium": mv.ImageClip(os.path.join(CHAR_DIR, "speaking_medium.png")),  # Correct usage of os.path.join
        "worried": mv.ImageClip(os.path.join(CHAR_DIR, "worried.png")),  # Correct usage of os.path.join
    }

    def __init__(self, script_path: str, output_path: Optional[str] = None) -> None:
        """
        Initialize VideoMaker instance.

        Args:
            script_path (str): Path to the script file.
            output_path (Optional[str], optional): Path to save the final video.
                If not provided, it will use the path in the [END] tag. Defaults to None.
        """
        self.script_path = script_path
        self.output_path = output_path
        self.current_font = fm.findfont(fm.FontProperties(family="Arial"))
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
        """
        Convert text to speech using Google TTS and convert it to a MoviePy clip
        with the specified start time and duration.

        Args:
            text (str): Text to convert to speech.
            start_time (float): Start time of the clip.
            duration (float, optional): Duration of the clip. Defaults to None.

        Returns:
            Tuple[mv.VideoClip, float]: A tuple containing the MoviePy clip and the
                duration of the clip.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
            # Convert text to speech using Google TTS
            gTTS(text=text, lang='en').save(tmp_audio_file.name)

            # Define the TTS clip and it's duration
            audio_clip = mv.AudioFileClip(tmp_audio_file.name)
            audio_duration = audio_clip.duration

            if duration is None:
                # If no duration is specified, use the audio duration
                clip_duration = audio_duration
            elif audio_duration > duration:
                # If the audio duration is longer than the specified duration, trim it
                audio_clip = audio_clip.subclip(0, duration)
                clip_duration = duration
            else:
                # If the audio duration is shorter than the specified duration, use the audio duration
                clip_duration = audio_duration

            # Create a black video clip with the same duration as the audio clip
            video_clip = mv.ColorClip(size=(1, 1), color=(0, 0, 0)).set_duration(clip_duration)

            # Combine the video and audio clips
            composite_clip = mv.CompositeVideoClip([video_clip.set_audio(audio_clip)])

            # Set the start time of the clip
            composite_clip = composite_clip.set_start(start_time)

            return composite_clip, clip_duration

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
        return mv.ImageClip(os.path.join(VideoMaker.STATICS_DIR, "bg_white.png")).set_duration(duration)  # Corrected path

    def add_emotion_clip(self, emotion_name: str, duration: float) -> float:
        """
        Adds an emotion clip to the video.

        Args:
            emotion_name (str): The name of the emotion to add.
            duration (float): The duration of the clip.

        Returns:
            float: The updated current time of the video.
        """
        # Get the emotion clip from the SPRITES dictionary based on the emotion name.
        emotion_clip = VideoMaker.SPRITES[emotion_name].set_duration(duration)
        
        # Calculate the height of the emotion clip by dividing its height by 1.4.
        emotion_height = int(emotion_clip.h // 1.4)
        
        # Resize the emotion clip to the calculated height and set its position to the bottom right of the video.
        # Also apply margins to the emotion clip to position it correctly.
        emotion_clip = emotion_clip.resize(height=emotion_height).set_position("bottom", "right").margin(bottom=10, opacity=0).margin(left=1500, opacity=0)
        
        # Set the start time of the clip to the current time of the video.
        emotion_clip = emotion_clip.set_start(self.current_time)
        
        # Add the emotion clip to the list of clips.
        self.clips.append(emotion_clip)
        
        # Update the current time of the video by adding the duration of the emotion clip.
        self.current_time += duration
        
        # Return the updated current time of the video.
        return self.current_time

    def add_espeech_clip(self, emotion_name: str, text: str, duration: float = None) -> float:
        """
        Adds an emotion clip with text-to-speech to the video.

        Args:
            emotion_name (str): The name of the emotion to add.
            text (str): The text to convert to speech.
            duration (float, optional): The duration of the clip. If not provided, the duration of the text-to-speech clip will be used.

        Returns:
            float: The updated current time of the video.
        """
        # Convert the text to speech and get the resulting clip and its duration.
        tts_clip, tts_duration = VideoMaker.google_tts_to_clip(text, self.current_time, duration)
        
        # If a duration is not provided, use the duration of the text-to-speech clip.
        emotion_duration = duration if duration else tts_duration
        
        # Get the emotion clip from the SPRITES dictionary based on the emotion name.
        emotion_clip = VideoMaker.SPRITES[emotion_name].set_duration(emotion_duration)
        
        # Calculate the height of the emotion clip by dividing its height by 1.4.
        emotion_height = int(emotion_clip.h // 1.4)
        
        # Resize the emotion clip to the calculated height and set its position to the bottom right of the video.
        # Also apply margins to the emotion clip to position it correctly.
        emotion_clip = emotion_clip.resize(height=emotion_height).set_position("bottom", "right").margin(bottom=10, opacity=0).margin(left=1500, opacity=0)
        
        # Set the start time of the emotion clip to the current time of the video.
        emotion_clip = emotion_clip.set_start(self.current_time)
        
        # Add the emotion clip and the text-to-speech clip to the list of clips.
        self.clips.append(emotion_clip)
        self.clips.append(tts_clip)
        
        # Update the current time of the video by adding the duration of the emotion clip.
        self.current_time += emotion_duration
        
        # Return the updated current time of the video.
        return self.current_time

    def add_textspeech_clip(self, text: str, duration: float = None, newline_threshold: int = 8) -> float:
        """
        Adds a text-to-speech clip to the video using PIL for text rendering.
        Improved error handling and logging added.
        """
        try:
            tts_clip, tts_duration = VideoMaker.google_tts_to_clip(text, self.current_time, duration)
            # Create a PIL Image
            img = Image.new('RGB', (1920, 1080), color='white')
            draw = ImageDraw.Draw(img)
            # Load a font
            font = ImageFont.truetype(self.current_font, 70)

            # For each newline_threshold words in the text (using .split()), 
            # insert a newline into the text
            words = text.split()
            new_text = ""
            for i in range(0, len(words), newline_threshold):
                new_text += " ".join(words[i:i+newline_threshold]) + "\n"
            text = new_text

            # Calculate text position to center it
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
            position = ((1920 - text_width) / 2, (1080 - text_height) / 2)
            # Draw the text
            draw.text(position, text, font=font, fill='black')
            # Convert PIL Image to numpy array
            img_array = np.array(img)
            # Create a MoviePy clip from the numpy array
            text_clip = mv.ImageClip(img_array).set_duration(tts_duration)
            # Add fade in and fade out effects
            text_clip = text_clip.fadeout(0.5).fadein(0.5)
            # Set the start time and audio
            text_clip = text_clip.set_start(self.current_time).set_audio(tts_clip.audio)
            # Add the text clip to the list of clips.
            self.clips.append(text_clip)
            # Update the current time of the video by adding the duration of the text clip.
            self.current_time += tts_duration
            # Return the updated current time of the video.
            return self.current_time
        except Exception as e:
            logger.error(f"Error adding textspeech clip: {e}")
            raise

    def add_insert_clip(self, video_path: str) -> float:
        """
        Adds a video clip to the list of clips, setting its start time to the current time of the video.

        Args:
            video_path (str): The path to the video file to be inserted.

        Returns:
            float: The updated current time of the video, which is the current time plus the duration of the inserted video clip.
        """
        # Create a new video clip from the given video file.
        insert_clip = mv.VideoFileClip(video_path)

        # Set the start time of the inserted video clip to the current time of the video.
        insert_clip = insert_clip.set_start(self.current_time)

        # Add the inserted video clip to the list of clips.
        self.clips.append(insert_clip)

        # Update the current time of the video by adding the duration of the inserted video clip.
        self.current_time += insert_clip.duration

        # Return the updated current time of the video.
        return self.current_time

    def export_final_video(self, save_path: str, fps: int):
        """
        Exports the final video as a single file.

        Args:
            save_path (str): The path to save the final video.
            fps (int): The frames per second of the final video.

        Raises:
            OSError: If there is an error exporting the video (e.g. invalid file type).
        """
        try:
            # Create a new CompositeVideoClip from the list of clips.
            final_video = mv.CompositeVideoClip(self.clips)

            # Export the final video to the given path, with the given fps, using 32 threads and the libx264 codec.
            final_video.write_videofile(save_path, fps=fps, threads=32, codec='libx264')

            # Log a success message, including the path and fps of the final video.
            logger.info(f"Final video '{save_path}' exported at {fps} FPS.")
        except OSError as e:
            # If the error is that there is no suitable output format, log an error message and exit with code 1.
            if "unable to find a suitable output format" in str(e).lower():
                logger.error("Output format error: Invalid output file type. Try again with a different file type (e.g. .mp4).")
                exit(1)

    def process_script(self):
        """
        Process a script into a video.

        :param script: The script to process.
        :return: None
        """
        # Define a function to parse commands.
        def get_command_parameters(command: str) -> list:
            return VideoMaker.remove_affix(command, ("[", "]")).split(" ")

        # Read the script.
        script = VideoMaker.read_script(self.script_path)
        # Get the initial background duration from the script.
        initial_duration = VideoMaker.parse_start_command(script)
        # Create the initial background clip.
        bg_clip = VideoMaker.create_initial_background_clip(initial_duration)
        # Add the background clip to the list of clips.
        self.clips.append(bg_clip)

        # Iterate over each line in the script.
        for line in script.splitlines():

            # Check if the line is a end command.
            if line.lower().startswith("[end"):
                # Get the command parameters.
                command = get_command_parameters(line)
                # If the output path wasn't specified, use the one in the script.
                if not self.output_path:
                    self.output_path = abspath(command[1])
                # Get the frames per second to export the video at.
                fps = int(command[2])
                # Export the final video.
                self.export_final_video(self.output_path, fps)

            # If the line is empty, skip it.
            elif line.lower().strip() == "":
                continue

            # If the line is an emotion command.
            elif line.lower().startswith("[emotion"):
                # Get the command parameters.
                command = get_command_parameters(line)
                # Get the name of the emotion to play.
                emotion_name = command[1]
                # Get the duration of the emotion to play.
                duration = float(command[2])
                # Add the emotion clip to the list of clips.
                self.add_emotion_clip(emotion_name, duration)
            # If the line is an espeech command.
            elif line.lower().startswith("[espeech"):
                # Get the command parameters.
                command = get_command_parameters(line)
                # Get the name of the emotion to play.
                emotion_name = command[1]
                # If the duration is "auto", don't specify a duration.
                if command[2] == "auto":
                    duration = None
                    text = " ".join(command[3:])
                else:
                    duration = float(command[2])
                    text = " ".join(command[3:])
                # Add the espeech clip to the list of clips.
                self.add_espeech_clip(emotion_name, text, duration)
            # If the line is an insert command.
            elif line.lower().startswith("[insert"):
                # Get the command parameters.
                command = get_command_parameters(line)
                # Get the path to the video to insert.
                video_path = command[1]
                # Add the insert clip to the list of clips.
                self.add_insert_clip(video_path)
            # If the line is a textspeech command.
            elif line.lower().startswith("[textspeech"):
                # Get the command parameters.
                command = get_command_parameters(line)
                # If the duration is "auto", don't specify a duration.
                if command[1] == "auto":
                    duration = None
                    text = " ".join(command[2:])
                else:
                    duration = float(command[1])
                    text = " ".join(command[2:])
                # Add the textspeech clip to the list of clips.
                self.add_textspeech_clip(text, duration)

def main() -> None:
    """
    Generate a video based on a script.

    Args:
        script_path (str): Path to the script file.
        output_path (Optional[str], optional): Path to save the final video.
            If not provided, it will use the path in the [END] tag. Defaults to None.
    """
    parser = argparse.ArgumentParser(description="Generate videos based on a script.")
    parser.add_argument("script_path", type=str, help="Path to the script file.")
    parser.add_argument("-o", "--output_path", type=str, help="Optional path to save the final video. If not provided, it will use the path in the [END] tag.")

    args = parser.parse_args()

    # Create a VideoMaker instance.
    video_maker = VideoMaker(args.script_path, args.output_path)

    # Process the script.
    video_maker.process_script()

if __name__ == '__main__':
    main()
