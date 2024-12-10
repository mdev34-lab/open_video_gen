from moviepy import *
from PIL import Image
import os

def get_character_images(sprites: dict, character_folder: str):
    character_images: tuple = tuple()
    for key in sprites.keys():
        character_images += (os.path.join(character_folder, f"{key}.png"),)
    return character_images

def load_sprites_recursively(char_dir: str):
    sprites: dict = {}
    for sprite_name in os.listdir(char_dir):
        if sprite_name.endswith(".png"):
            sprites[sprite_name[:-4]] = ImageClip(os.path.join(char_dir, sprite_name))
    return sprites

def get_character_average_size(character_images: tuple) -> tuple[int, int]:
    return tuple(map(
        lambda x: int(sum(x) / len(x)),
        zip(*[Image.open(i).size for i in character_images[:3]])
    ))

class WhiteClip(ColorClip):
    def __init__(self, size, *args, **kwargs):
        super().__init__(size=size, color=(255, 255, 255), *args, **kwargs)

class CharacterClip(ImageClip):
    def __init__(self, character, CHARACTERS: tuple, CHARACTER_IMAGES_FOLDER: str, size: tuple[int, int] = None, *args, **kwargs):
        if character not in CHARACTERS:
            raise ValueError(f"Character '{character}' not in {CHARACTERS}")
        super().__init__(os.path.join(CHARACTER_IMAGES_FOLDER, f"{character}.png"), *args, **kwargs)
        self.character = character