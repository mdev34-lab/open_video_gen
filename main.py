#!/usr/bin/env python3

import argparse
import tempfile
import os
import logging
import sys
import numpy as np
import re
import asyncio  # Add this import at the top of your file

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
    def parse_start_command(script: str) -> Tuple[int, Tuple[int, int]]:
        if not script.splitlines()[0].lower().startswith("[start"):
            raise VideoMaker.InvalidScriptError("The first line of the script must be '[START]'.")
        else:
            try:
                command = utils.remove_affix(script.splitlines()[0], ("[", "]")).split(" ")
                duration = int(command[1])
                if len(command) > 2:
                    resolution = tuple(map(int, command[2].split("x")))
                else:
                    resolution = VideoMaker.RESOLUTION  # Default resolution
                return duration, resolution
            except (IndexError, ValueError):
                raise VideoMaker.InvalidScriptError("Invalid '[START]' command. Example: '[START 5 1920x1080]'")

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
        
        # Calculate the character's size based on the resolution.
        # For example, you can use a fixed ratio of the character's size to the resolution.
        character_size_ratio = 0.1  # Adjust this value to change the character's size.
        character_width = int(self.RESOLUTION[0] * character_size_ratio)
        character_height = int(self.RESOLUTION[1] * character_size_ratio)
        
        # Resize the emotion clip to the calculated size.
        emotion_clip = emotion_clip.resized(width=character_width, height=character_height)\
            .with_position("bottom", "right")\
            .with_effects([vfx.Margin(bottom=10, left=1500, opacity=0)])
        
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

    async def add_textspeech_clip(self, text: str, duration: float = None, newline_threshold: int = 8) -> float:
        """
        Adds a text-to-speech clip to the video using PIL for text rendering.
        Improved error handling and logging added.
        """
        try:
            # Await the coroutine to get the actual result
            tts_clip, tts_duration = await VideoMaker.edge_tts_to_clip(text, self.current_time, duration)
            # Create a PIL Image
            img = Image.new('RGB', VideoMaker.RESOLUTION, color='white')  # Use RESOLUTION constant
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
            position = ((VideoMaker.RESOLUTION[0] - text_width) / 2, (VideoMaker.RESOLUTION[1] - text_height) / 2)  # Use RESOLUTION constant
            # Draw the text
            draw.text(position, text, font=font, fill='black')
            # Convert PIL Image to numpy array
            img_array = np.array(img)
            # Create a MoviePy clip from the numpy array
            text_clip = ImageClip(img_array).with_duration(tts_duration)
            # Add fade in and fade out effects
            text_clip: TextClip = text_clip.with_effects([vfx.FadeOut(0.5), vfx.FadeIn(0.5)])
            # Set the start time and audio
            text_clip = text_clip.with_start(self.current_time).with_audio(tts_clip.audio)
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
        """
        Process a script into a video.
        """
        # Define a function to parse commands.
        def get_command_parameters(command: str) -> list:
            return utils.remove_affix(command, ("[", "]")).split(" ")

        # Read the script.
        script = VideoMaker.read_script(self.script_path)
        # Get the initial background duration from the script.
        initial_duration, VideoMaker.RESOLUTION = VideoMaker.parse_start_command(script)
        # Create the initial background clip.
        bg_clip = VideoMaker.create_initial_background_clip(initial_duration, VideoMaker.RESOLUTION)
        video_width, video_height = bg_clip.size  # Get video dimensions
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
                # Await the espeech clip addition
                await self.add_espeech_clip(emotion_name, text, duration)

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
                # Await the textspeech clip addition
                await self.add_textspeech_clip(text, duration)

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

