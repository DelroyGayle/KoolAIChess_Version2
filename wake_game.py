import os
import sys
import time
from os import system, name

from wake_constants import Rival
from wake_position import Position
from make_copy import makecopy
from copy import deepcopy

CURRENT_VERSION = "2.0.0"
# VERSION 1.0.0 is at https://github.com/DelroyGayle/KoolAIChess


def clear_screen():
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

        # TODO - May remove.
        self.whose_move = {
            Rival.PLAYER: "Player",
            Rival.COMPUTER: "Computer",
        }

    def clone(self):
        newclone = WakeGame()
        for key, value in vars(self).items():
            setattr(newclone, key, makecopy(value))

        return newclone

#  TODO

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result
   
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        result.score = self.score[:] #  [0,0] hence shallow copy
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result
