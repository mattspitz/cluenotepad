#!/usr/bin/env python

from collections import deque, namedtuple
import datetime
import logging
import os
import pickle
import sys

import Levenshtein

_logger = logging.getLogger(__name__)

class Board:
    people = [
            "Mustard",
            "Plum",
            "Green",
            "Peacock",
            "Scarlet",
            "White"
            ]

    weapons = [
            "Knife",
            "Candlestick",
            "Revolver",
            "Rope",
            "LeadPipe",
            "Wrench"
            ]

    rooms = [
            "Hall",
            "Lounge",
            "DiningRoom",
            "Kitchen",
            "Ballroom",
            "Conservatory",
            "BilliardRoom",
            "Library",
            "Study"
            ]

Question = namedtuple("Question", "person weapon room")
Turn = namedtuple("Turn", "question asker answerer")

class Game(object):
    def __init__(self, players):
        super(Game, self).__init__()
        self.players = players
        self.turns = deque()
        self.name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.clue")

    def add_turn(self, turn):
        _logger.debug("Adding turn: {0}".format(turn))
        self.turns.appendleft(turn)

    def print_current_state(self):
        """ Prints the current game state, rebuilt from scratch from all turns. """
        # TODO construct game state
        print("Players: {0}".format(", ".join(self.players)))
        # TODO print game state

    def show_turns(self):
        for i, turn in enumerate(self.turns, 1):
            print("{:d}. {}".format(i, turn))

    def undo_last_turn(self):
        self.turns.popleft()

    def dump_state(self):
        pickle.dump(self, open(self.name, "w"))

def find_best(s, options):
    """ Given a raw input string and a series of possibilities, returns the option with the lowest Levenshtein distance, representing our best guess. """
    return sorted(options, key=lambda opt: Levenshtein.distance(s.lower(), opt.lower()))[0]

def get_turn(players):
    while True:
        try:
            raw_turn = raw_input("Enter turn as 'asker person weapon room answerer': ")
            asker, person, weapon, room, answerer = map(lambda s: s.strip(), raw_turn.split())
            break
        except Exception:
            logging.exception("Couldn't parse input string")

    return Turn(
            Question(find_best(person, Board.people),
                find_best(weapon, Board.weapons),
                find_best(room, Board.rooms)),
            find_best(asker, players),
            find_best(answerer, players + ["-"]) # - indicates that no one answered it
            )

def game_loop(game=None):
    while True:
        game.print_current_state()
        turn = get_turn(game.players)
        game.add_turn(turn)
        game.dump_state()

def get_player_names():
    raw_player_names = raw_input("Enter player names, clockwise and space-delimited: ")
    return [ name.strip() for name in raw_player_names.split() ]

def main():
    if len(sys.argv) > 1:
        game = pickle.load(open(sys.argv[1]))
    else:
        players = get_player_names()
        game = Game(players)
    game_loop(game)

if __name__ == "__main__":
    log_level = logging.INFO
    if os.environ.get("DEBUG"):
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)

    main()
