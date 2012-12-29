#!/usr/bin/env python

from collections import defaultdict, namedtuple
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
ALL_CARDS = set(itertools.chain(*BOARD.itervalues()))

Question = namedtuple("Question", "person weapon room")
Turn = namedtuple("Turn", "question asker answerer card")

class IllegalGameStateException(Exception):
    pass

class Game(object):
    def __init__(self, player, all_players, player_cards):
        super(Game, self).__init__()
        self.player = player
        self.all_players = all_players
        self.player_cards = player_cards
        self.turns = [] # used as a stack
        self.name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.clue")

    def add_turn(self, turn):
        _logger.debug("Adding turn: {}".format(turn))
        self.turns.append(turn)

    def players_between(self, asker, answerer):
        """ Given a start player, returns the players, in order, between asker and answerer, non-inclusive.  If answerer is -, returns all players except the asker, in order. """

        asker_pos = self.all_players.index(asker)
        answerer_pos = self.all_players.index(answerer) if answerer != "-" else asker_pos

        if answerer_pos > asker_pos:
            return self.all_players[(asker_pos + 1) : answerer_pos]
        else:
            return (self.all_players + self.all_players)[(asker_pos + 1) : (len(self.all_players) + answerer_pos)]

    def print_current_state(self):
        """ Prints the current game state, rebuilt from scratch from all turns.

        For each item-player combination, we store one of four states, YES, NO, MAYBE, or UNK (unknown).  A next iteration could be smart about which questions to ask next to reveal more information, but we're not there yet.
        """
        YES, NO, MAYBE, UNK = range(1, 5)

        game_state = defaultdict(dict) # represents state by card-player combinations
        for card in ALL_CARDS:
            for player in self.all_players:
                game_state[card][player] = UNK

        def set_no(card, player):
            if game_state[card][player] == YES:
                raise IllegalGameStateException("We know that {} has {} but we're trying to set the state to NO.".format(player, card))
            else:
                _logger.debug("Setting {} to NO for {}".format(card, player))
                game_state[card][player] = NO

        def set_yes(card, player):
            if game_state[card][player] == NO:
                raise IllegalGameStateException("We know that {} doesn't have {} but we're trying to set the state to YES.".format(player, card))
            else:
                _logger.debug("Setting {} to YES for {}".format(card, player))
                game_state[card][player] = YES
                for other_player in game_state[card]:
                    if player != other_player:
                        set_no(card, other_player)

        def set_maybe(card, player):
            if game_state[card][player] not in (YES, NO):
                _logger.debug("Setting {} to MAYBE for {}".format(card, player))
                game_state[card][player] = MAYBE
            else:
                _logger.debug("Skipping MAYBE on {} for {}.  Card was already {}.".format(card, player, "YES" if game_state[card][player] == YES else "NO"))

        # set up the player's cards
        for card in ALL_CARDS:
            if card in self.player_cards:
                set_yes(card, self.player)
            else:
                set_no(card, self.player)

        maybes_by_player = defaultdict(list) # represents maybe-state by player (resolved later)
        for turn in self.turns:
            _logger.debug("Handling turn: {}".format(turn))

            # we know that all players in between have none of these cards
            for player in self.players_between(turn.asker, turn.answerer):
                for card in turn.question:
                    set_no(card, player)

            # handle the answerer (if answered and it's not the player playing)
            if turn.answerer not in ["-", self.player]:
                if turn.card is not None:
                    set_yes(turn.card, turn.answerer)
                else:
                    for card in turn.question:
                        set_maybe(card, turn.answerer)
                    maybes_by_player[turn.answerer].append(turn.question)

        # TODO resolve maybes

        # sanity check: there can't be two people who've answered yes on the same item
        for card, card_state in game_state.iteritems():
            yes_players = filter(lambda (k,v): v == YES, card_state.items())
            if len(yes_players) > 1:
                raise IllegalGameStateException("{:d} players have {} marked as yes! ({})".format(len(yes_players), card, ",".join(yes_players)))

        # sanity check: there can't be two items in a group with everyone answering no
        for group, cards in BOARD.iteritems():
            allno_cards = filter(
                    lambda card: all(v == NO for k,v in game_state[card].iteritems()),
                    cards
                    )
            if len(allno_cards) > 1:
                raise IllegalGameStateException("More than one card in {} has everyone answering NO ({}).  Can't be more than one per group in the center envelope!".format(group, ",".join(allno_cards)))

        print("Players: {0}".format(", ".join(self.all_players)))

        output_table = []
        for group, descriptor in [
                ("people", "Murderer"),
                ("weapons", "Weapon"),
                ("rooms", "Scene of the crime")]:
            output_table.append( ("", "Yes", "No", "Maybe") )

            for card in BOARD[group]:
                card_state = game_state[card]
                players_by_val = {
                        V : [ player for player,val in card_state.iteritems() if val == V ]
                        for V in set(card_state.values())
                        }
                out = defaultdict(str)

                if YES in players_by_val:
                    out["Yes"] = players_by_val[YES][0]
                else:
                    no = players_by_val.get(NO, [])
                    if len(no) == len(card_state): # everyone answered NO
                        out["Yes"] = "**{}**".format(descriptor)
                    else:
                        maybe = players_by_val.get(MAYBE, [])
                        out["No"] = ", ".join(filter(lambda x: x != self.player, no))
                        out["Maybe"] = ", ".join(filter(lambda x: x != self.player, maybe))
                output_table.append( (card, out["Yes"], out["No"], out["Maybe"]) )
            output_table.append( ("", "", "", "") )

        print_table(output_table)

    def show_turns(self):
        for i, turn in enumerate(self.turns, 1):
            print("{:d}. {}".format(i, turn))

    def undo_last_turn(self):
        self.turns.pop()

    def dump_state(self):
        pickle.dump(self, open(self.name, "w"))

def print_table(table):
    FILL_SPACE = 8
    col_widths = [ max(map(len, [ row[i] for row in table ])) for i in range(len(table[0])) ]

    for row in table:
        print((" "*FILL_SPACE).join( s.ljust(col_widths[i]) for i,s in enumerate(row) ))

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
            best_card = find_best(card, ALL_CARDS) if card is not None else None
            if best_card is not None:
                if answerer == "-":
                    raise Exception("If card is provided, answerer must not be -.")

                if best_card not in (question.person, question.weapon, question.room):
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
            turn = get_turn(game.all_players)
        except EndOfGameException:
            return
        game.add_turn(turn)
        game.dump_state()

def get_player_names():
    raw_player_names = raw_input("Enter all player names, clockwise and space-delimited: ")
    return [ name.strip() for name in raw_player_names.split() ]

def get_this_player(all_players):
    raw_player_name = raw_input("Enter your name: ")
    return find_best(raw_player_name, all_players)

def get_player_cards():
    raw_known = raw_input("Enter your cards, space-delimited: ")
    return [ find_best(card, ALL_CARDS) for card in raw_known.split() ]

def main():
    if len(sys.argv) > 1:
        game = pickle.load(open(sys.argv[1]))
    else:
        all_players = get_player_names()
        player = get_this_player(all_players)
        player_cards = get_player_cards()
        game = Game(player, all_players, player_cards)

    game_loop(game)

if __name__ == "__main__":
    log_level = logging.INFO
    if os.environ.get("DEBUG"):
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)

    main()
