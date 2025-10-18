import os
import sys
import time
from os import system, name

from wake_constants import Rival
from wake_position import Position

CURRENT_VERSION = "2.0.0"
# VERSION 1.0.0 is at https://github.com/DelroyGayle/KoolAIChess


def clear():
    # Windows
    if name == "nt":
        _ = system("cls")
    else:
        _ = system("clear")


class WakeGame:

    def __init__(self):
        self.history = []
        self.position = Position()
        self.is_over = False
        self.score = [0, 0]

        self.rival_to_move = {
            Rival.PLAYER: "Player",
            Rival.COMPUTER: "Computer",
        }
