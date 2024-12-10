from moviepy import *

# Create a solid color clip
clip = ColorClip(size=(1920, 1080), color=(255, 0, 0), duration=5)  # Red color, 5 seconds duration

# Write the result to a file
clip.write_videofile("test_video.mp4", fps=24) 