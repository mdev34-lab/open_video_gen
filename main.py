#!/usr/bin/env python3

import argparse
import tempfile
import os
import logging
import sys
import numpy as np
import re
import asyncio  # Add this import at the top of your file
import textwrap  # Import the textwrap module
import xml.etree.ElementTree as ET

import utils
from utils import CharacterClip

from os.path import abspath, dirname
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm
import edge_tts
from loguru import logger
from moviepy import *
import cv2 as cv

# The star of the show: VideoMaker class.
class VideoMaker:
    ROOT_DIR = abspath(dirname(__file__))
    CHAR_DIR = os.path.join(ROOT_DIR, "character")  # Correct usage of os.path.join
    STATICS_DIR = os.path.join(ROOT_DIR, "statics")  # Correct usage of os.path.join

    # Sprite cache.
    SPRITES: dict = utils.load_sprites_recursively(CHAR_DIR)
    # Tuple of character images
    CHARACTER_IMAGES: tuple = utils.get_character_images(SPRITES, CHAR_DIR)
    CHARACTERS: tuple = tuple(SPRITES.keys())
    # Get a estimate of the character size
    CHARACTER_AVERAGE_SIZE: tuple = utils.get_character_average_size(CHARACTER_IMAGES)
    # Define the RESOLUTION constant
    RESOLUTION = (1920, 1080)
    TTS_VOICE = "en-US-AndrewMultilingualNeural"

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
        # Initialize the current font
        self.current_font = fm.findfont(fm.FontProperties(family="Arial"))
        self.clips = []
        self.current_time = 0

    @staticmethod
    async def edge_tts_to_clip(text: str, start_time: float, duration: float = None) -> Tuple[VideoClip, float]:
        """
        Convert text to speech using Azure TTS and convert it to a MoviePy clip
        with the specified start time and duration.

        Args:
            text (str): Text to convert to speech.
            start_time (float): Start time of the clip.
            duration (float, optional): Duration of the clip. Defaults to None.

        Returns:
            Tuple[VideoClip, float]: A tuple containing the MoviePy clip and the
                duration of the clip.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
            # Convert text to speech using Google TTS
            await utils.edge_tts_to_audiofile(text, VideoMaker.TTS_VOICE, tmp_audio_file.name)

            # Define the TTS clip and its duration
            audio_clip = AudioFileClip(tmp_audio_file.name)
            audio_duration = audio_clip.duration

            if duration is None:
                # If no duration is specified, use the audio duration
                clip_duration = audio_duration
            elif audio_duration > duration:
                # If the audio duration is longer than the specified duration, trim it
                audio_clip: AudioClip = audio_clip.subclipped(0, duration)
                clip_duration = duration
            else:
                # If the audio duration is shorter than the specified duration, use the audio duration
                clip_duration = audio_duration

            # Create a black video clip with the same duration as the audio clip
            video_clip = utils.BlackClip((1, 1)).with_duration(clip_duration)

            # Combine the video and audio clips
            composite_clip = video_clip.with_audio(audio_clip)

            # Set the start time of the clip
            composite_clip = composite_clip.with_start(start_time)

            return composite_clip, clip_duration

    @staticmethod
    def read_script(script_path: str) -> str:
        with open(script_path, "r", encoding="utf-8") as script_file:
            return script_file.read()

    @staticmethod
    def create_initial_background_clip(duration: int, resolution: Tuple[int, int]) -> ImageClip:
        return utils.WhiteClip(resolution).with_duration(duration)

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
        emotion_clip = CharacterClip(emotion_name, \
                                    VideoMaker.CHARACTERS, \
                                    VideoMaker.CHAR_DIR, \
                                    duration=duration)
        
        # Resize the emotion clip using CHARACTER_AVERAGE_SIZE
        emotion_clip = emotion_clip.resized(VideoMaker.CHARACTER_AVERAGE_SIZE)
        
        # Calculate the height of the emotion clip by dividing its height by 1.4
        emotion_height = int(emotion_clip.h // 1.4) - 50
        
        # Resize the emotion clip to the calculated height and set its position
        video_width, video_height = self.clips[0].w, self.clips[0].h
        character_width = emotion_clip.w
        left_margin = video_width - character_width - 100  # 100 pixels from the right edge
        emotion_clip = emotion_clip.resized(height=emotion_height)\
            .with_position("bottom", "right")\
            .with_effects([vfx.Margin(bottom=10, left=left_margin, opacity=0)])
        
        # Set the start time of the clip to the current time of the video.
        emotion_clip = emotion_clip.with_start(self.current_time)
        
        # Add the emotion clip to the list of clips.
        self.clips.append(emotion_clip)
        
        # Update the current time of the video by adding the duration of the emotion clip.
        self.current_time += duration
        
        # Return the updated current time of the video.
        return self.current_time

    async def add_espeech_clip(self, emotion_name: str, text: str, duration: float = None) -> float:
        """
        Adds an emotion clip with text-to-speech to the video.

        Args:
            emotion_name (str): The name of the emotion to add.
            text (str): The text to convert to speech.
            duration (float, optional): The duration of the clip. If not provided, the duration of the text-to-speech clip will be used.

        Returns:
            float: The updated current time of the video.
        """
        tts_clip, tts_duration = await VideoMaker.edge_tts_to_clip(text, self.current_time, duration)
        
        # If a duration is not provided, use the duration of the text-to-speech clip.
        emotion_duration = duration if duration else tts_duration
        
        # Ensure the emotion clip is created with the correct duration
        emotion_clip = CharacterClip(emotion_name, VideoMaker.CHARACTERS, VideoMaker.CHAR_DIR, duration=emotion_duration)
        emotion_clip = emotion_clip.resized(VideoMaker.CHARACTER_AVERAGE_SIZE)
        
        # Calculate the height of the emotion clip by dividing its height by 1.4.
        emotion_height = int(emotion_clip.h // 1.4) - 50
        
        # Resize the emotion clip to the calculated height and set its position to the bottom right of the video.
        # Also apply margins to the emotion clip to position it correctly.
        video_width, video_height = self.clips[0].w, self.clips[0].h
        character_width = emotion_clip.w
        left_margin = video_width - character_width - 100  # 100 pixels from the right edge
        emotion_clip = emotion_clip.resized(height=emotion_height)\
            .with_position("bottom", "right")\
            .with_effects([vfx.Margin(bottom=10, left=left_margin, opacity=0)])
        
        # Set the start time of the emotion clip to the current time of the video.
        emotion_clip = emotion_clip.with_start(self.current_time)
        
        # Add the emotion clip and the text-to-speech clip to the list of clips.
        self.clips.append(emotion_clip)
        self.clips.append(tts_clip)
        
        # Update the current time of the video by adding the duration of the emotion clip.
        self.current_time += emotion_duration
        
        # Return the updated current time of the video.
        return self.current_time

    async def add_textspeech_clip(self, text: str, duration: float = None, bg_clip: VideoClip = None) -> float:
        """Adds a text-to-speech clip with dynamic text wrapping."""
        try:
            tts_clip, tts_duration = await VideoMaker.edge_tts_to_clip(text, self.current_time, duration)

            img = Image.fromarray(np.array(bg_clip.get_frame(0)).astype('uint8'))
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(self.current_font, 70)  # Keep font size consistent

            # Calculate available width for text (with margins)
            margin = 50  # Adjust margin as needed
            max_width = VideoMaker.RESOLUTION[0] - 2 * margin

            # Wrap the text
            wrapped_text = textwrap.fill(text, width=int(max_width / (draw.textbbox((0, 0), "A", font=font)[2]-draw.textbbox((0, 0), "", font=font)[2])))

            # Calculate text position to center it vertically as well
            lines = wrapped_text.splitlines()
            total_text_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines])
            y_text = (VideoMaker.RESOLUTION[1] - total_text_height) / 2
            x_text = VideoMaker.RESOLUTION[0] / 2

            for line in lines:
                text_width, text_height = draw.textbbox((0, 0), line, font=font)[2:]
                draw.text((x_text-(text_width/2), y_text), line, font=font, fill='black')
                y_text += text_height

            img_array = np.array(img)
            text_clip = ImageClip(img_array).with_duration(tts_duration)
            text_clip: TextClip = text_clip.with_effects([vfx.FadeOut(0.5), vfx.FadeIn(0.5)])
            text_clip = text_clip.with_start(self.current_time).with_audio(tts_clip.audio)
            self.clips.append(text_clip)
            self.current_time += tts_duration
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
        insert_clip = VideoFileClip(video_path)

        # Set the start time of the inserted video clip to the current time of the video.
        insert_clip = insert_clip.with_start(self.current_time)

        # Add the inserted video clip to the list of clips.
        self.clips.append(insert_clip)

        # Update the current time of the video by adding the duration of the inserted video clip.
        self.current_time += insert_clip.duration

        # Return the updated current time of the video.
        return self.current_time

    def export_final_video(self, save_path: str, fps: int):
        try:
            final_video = CompositeVideoClip(self.clips)
            final_video.write_videofile(save_path, fps=fps, threads=32, codec='libx264')
            logger.info(f"Final video '{save_path}' exported at {fps} FPS.")
        except OSError as e:
            if "unable to find a suitable output format" in str(e).lower():
                logger.error("Output format error: Invalid output file type.")
                exit(1)
        finally:
            # Close all clips
            for clip in self.clips:
                try:
                    clip.close()
                except:
                    pass
            try:
                final_video.close()
            except:
                pass

    async def process_script(self):
        """Process an XML script into a video."""
        try:
            tree = ET.parse(self.script_path)
            root = tree.getroot()

            if root.tag != "video":
                raise VideoMaker.InvalidScriptError("Root element must be <video>")

            resolution_str = root.get("resolution", "1920x1080")  # Default resolution
            try:
                VideoMaker.RESOLUTION = tuple(map(int, resolution_str.split("x")))
            except ValueError:
                raise VideoMaker.InvalidScriptError("Invalid resolution format (e.g., 1920x1080)")

            bg_clip = utils.WhiteClip(VideoMaker.RESOLUTION).with_duration(0) # Initial background clip
            self.clips.append(bg_clip)
            max_end_time = 0

            for element in root:
                if element.tag == "emotion":
                    name = element.get("name")
                    duration = float(element.get("duration"))
                    self.add_emotion_clip(name, duration)
                    max_end_time = max(max_end_time, self.current_time)

                elif element.tag == "espeech":
                    emotion = element.get("emotion")
                    duration_str = element.get("duration", "auto")
                    duration = float(duration_str) if duration_str != "auto" else None
                    text = element.text.strip()
                    await self.add_espeech_clip(emotion, text, duration)
                    max_end_time = max(max_end_time, self.current_time)

                elif element.tag == "insert":
                    path = element.get("path")
                    self.add_insert_clip(path)
                    max_end_time = max(max_end_time, self.current_time)

                elif element.tag == "textspeech":
                    duration_str = element.get("duration", "auto")
                    duration = float(duration_str) if duration_str != "auto" else None
                    text = element.text.strip()
                    await self.add_textspeech_clip(text, duration, bg_clip)
                    max_end_time = max(max_end_time, self.current_time)

                elif element.tag == "end":
                    output_path = element.get("output", "output.mp4") # Default output
                    fps = int(element.get("fps", 24)) # Default FPS
                    self.clips[0] = self.clips[0].with_duration(max_end_time)
                    self.export_final_video(output_path, fps)
                    return # Exit after exporting
                elif element.tag == "background":
                    color = element.get("color", "white")
                    rgb_color = self.get_rgb_color(color)
                    bg_clip = utils.ColorClip(VideoMaker.RESOLUTION, rgb_color).with_duration(0)
                    self.clips[0] = bg_clip
                elif element.tag == "start":
                    pass
                else:
                    logger.warning(f"Unknown element: {element.tag}")
            self.clips[0] = self.clips[0].with_duration(max_end_time)
            self.export_final_video("output.mp4", 24)

        except ET.ParseError as e:
            raise VideoMaker.InvalidScriptError(f"XML parsing error: {e}")
        except FileNotFoundError:
            raise VideoMaker.InvalidScriptError(f"Script file not found: {self.script_path}")
        except ValueError as e: # Handle invalid float conversions
            raise VideoMaker.InvalidScriptError(f"Invalid value in script: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def get_rgb_color(color_name: str) -> tuple:
        def convert_to_rgb(color: str):
            color = color.lstrip('#')
            r = int(color[:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            return (r, g, b)

        if color_name.lower().startswith("#"): return convert_to_rgb(color_name)

        colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
            "lightgrey": (200, 200, 200),
        }
        return colors.get(color_name.lower(), (255, 255, 255))  # Default to white if color not found

    class InvalidScriptError(Exception):
        """Custom exception for invalid script format."""
        pass

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

    # Process the script asynchronously
    asyncio.run(video_maker.process_script())  # Use asyncio.run to await the coroutine

if __name__ == '__main__':
    main()
