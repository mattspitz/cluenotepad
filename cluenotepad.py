#!/usr/bin/env python

from collections import defaultdict, deque, namedtuple
import datetime
import itertools
import logging
import os
import pickle
import sys

import Levenshtein

_logger = logging.getLogger(__name__)

BOARD = {
    "people": [
            "Mustard",
            "Plum",
            "Green",
            "Peacock",
            "Scarlet",
            "White"
            ],

    "weapons": [
            "Knife",
            "Candlestick",
            "Revolver",
            "Rope",
            "Pipe",
            "Wrench"
            ],

    "rooms": [
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
    }

Question = namedtuple("Question", "person weapon room")
Turn = namedtuple("Turn", "question asker answerer card")

class Game(object):
    def __init__(self, players, known_cards):
        super(Game, self).__init__()
        self.players = players
        self.known_cards = known_cards
        self.turns = deque()
        self.name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.clue")

    def add_turn(self, turn):
        _logger.debug("Adding turn: {0}".format(turn))
        self.turns.appendleft(turn)

    def print_current_state(self):
        """ Prints the current game state, rebuilt from scratch from all turns.

        For each item-player combination, we store one of three states, YES, NO, or MAYBE.  A next iteration could be smart about which questions to ask next to reveal more information, but we're not there yet.
        """
        YES, NO, MAYBE = range(1, 4)

        game_state = defaultdict(lambda: defaultdict(dict))
        for group, items in BOARD.iteritems():
            for item in items:
                for player in self.players:
                    game_state[group][item][player] = MAYBE

        self.known_cards
        print("Players: {0}".format(", ".join(self.players)))
        # TODO print game state

    def show_turns(self):
        for i, turn in enumerate(reversed(self.turns), 1):
            print("{:d}. {}".format(i, turn))

    def undo_last_turn(self):
        self.turns.popleft()

    def dump_state(self):
        pickle.dump(self, open(self.name, "w"))

def find_best(s, options):
    """ Given a raw input string and a series of possibilities, returns the option with the lowest Levenshtein distance, representing our best guess. """
    return sorted(options, key=lambda opt: Levenshtein.distance(s.lower(), opt.lower()))[0]

class EndOfGameException(Exception):
    pass

def get_turn(players):
    while True:
        try:
            raw_turn = raw_input("Enter turn as 'asker person weapon room answerer [card]': ")
            split = map(lambda s: s.strip(), raw_turn.split())
            if len(split) == 5:
                asker, person, weapon, room, answerer = split
                card = None
            elif len(split) == 6:
                asker, person, weapon, room, answerer, card = split
            else:
                raise Exception("Not enough information specified.")

            question = Question(find_best(person, BOARD["people"]),
                    find_best(weapon, BOARD["weapons"]),
                    find_best(room, BOARD["rooms"]))
            best_card = find_best(card, itertools.chain(*BOARD.itervalues())) if card is not None else None
            if best_card is not None and best_card not in (question.person, question.weapon, question.room):
                raise Exception("Card shown ({}) must be one from the question ({})".format(best_card, question))

            return Turn(question,
                    find_best(asker, players),
                    find_best(answerer, players + ["-"]), # - indicates that no one answered it
                    best_card)
        except EOFError:
            raise EndOfGameException()
        except Exception:
            logging.exception("Couldn't parse input string")

def game_loop(game=None):
    while True:
        game.print_current_state()
        try:
            turn = get_turn(game.players)
        except EndOfGameException:
            return
        game.add_turn(turn)
        game.dump_state()

def get_player_names():
    raw_player_names = raw_input("Enter all player names, clockwise and space-delimited: ")
    return [ name.strip() for name in raw_player_names.split() ]

def get_known_cards(all_players):
    known = defaultdict(set)
    while True:
        raw_known = raw_input("Enter known cards as 'player card1 card2 card3...' (enter to exit): ")
        if raw_known.strip():
            player, cards = raw_known.split(" ", 1)
            known[find_best(player, all_players)].update({
                find_best(card, itertools.chain(*BOARD.itervalues())) for card in cards.split() })
        else:
            return known

def main():
    if len(sys.argv) > 1:
        game = pickle.load(open(sys.argv[1]))
    else:
        players = get_player_names()
        known_cards = get_known_cards(players)
        game = Game(players, known_cards)
    game_loop(game)

if __name__ == "__main__":
    log_level = logging.INFO
    if os.environ.get("DEBUG"):
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)

    main()
