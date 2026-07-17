import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pygame.pkgdata")

import logging

import pygame

from .path import get_path

# Initialize pygame mixer
pygame.mixer.init()


def load_sound(filename: str):
    """
    Tenta carregar um arquivo de som a partir de app/static/sounds.
    Retorna o objeto Sound se existir e for válido, caso contrário None.
    """
    sound_path = get_path(f"app/static/sounds/{filename}")
    if os.path.exists(sound_path):
        try:
            return pygame.mixer.Sound(sound_path)
        except Exception as e:
            logging.error(f"Erro carregando {filename}: {e}")
            return None
    else:
        logging.error(f"Arquivo de som não encontrado: {sound_path}")
        return None


# Carregar sons
beep_sound = load_sound("beep.wav")
error_sound = load_sound("error.mp3")


async def beep():
    """
    Executa o som de beep.
    """
    if beep_sound is not None:
        try:
            beep_sound.play()
        except Exception:
            pass  # Falha silenciosa


async def error():
    """
    Executa o som de erro.
    """
    if error_sound is not None:
        try:
            error_sound.play()
        except Exception:
            pass  # Falha silenciosa
