#!/usr/bin/env python

import yaml
from functools import lru_cache
from trello import TrelloClient
from dave.log import logger


class TrelloBoard(object):
    def __init__(self, api_key, token):
        """Creates a TrelloBoard object

        :param api_key: (str) Your Trello api key https://trello.com/1/appKey/generate
        :param token:  (str) Your Trello token
        """
        self.tc = TrelloClient(api_key=api_key, token=token)
        self._ab_cache = {}

    @property
    def boards(self):
        """All the boards that can be accessed

        :return: (Board) list of Board
        """
        return self.tc.list_boards()

    @property
    def addressbook(self):
        board = self._board("Address Book")
        resp = {}
        for l in board.list_lists():
            for card in l.list_cards():
                info = yaml.load(card.desc)
                if info:
                    resp[info["id"]] = {"name": card.name, "slack": info["slack"]}
        return resp

    @lru_cache(maxsize=128)
    def _org_id(self, team_name):
        """Get the id of a Trello team

        :param team_name:
        :return:
        """
        orgs = self.tc.list_organizations()
        for org in orgs:
            if org.name == team_name:
                return org.id

    @lru_cache(maxsize=128)
    def _board(self, board_name):
        board = [b for b in self.boards if b.name == board_name]
        if board:
            return board[0]

    @lru_cache(maxsize=128)
    def _member(self, member_id, board_name):
        member_id = str(member_id)
        board = self._board(board_name)

        for l in board.list_lists():
            for card in l.list_cards():
                if card.desc == member_id:
                    return card

    @lru_cache(maxsize=128)
    def _label(self, label_name, board_name):
        board = self._board(board_name)
        label = [l for l in board.get_labels() if l.name == label_name]
        if label:
            return label[0]

    def create_board(self, board_name, team_name=None):
        template = self._board("Meetup Template")
        board = self._board(board_name)
        org_id= self._org_id(team_name=team_name)

        if not board:
            self.tc.add_board(board_name=board_name, source_board=template, organization_id=org_id)

    def add_rsvp(self, name, member_id, board_name):
        member_id = str(member_id)
        board = self._board(board_name)
        rsvp_list = board.list_lists()[0]

        if not self._member(member_id, board_name):
            rsvp_list.add_card(name=name, desc=member_id)
        logger.debug("add_rsvp: ", self._member.cache_info())

    def cancel_rsvp(self, member_id, board_name):
        logger.debug("Cancelling RSVP for members id {} at {}".format(member_id, board_name))
        card = self._member(member_id, board_name)
        logger.debug("Card for member id {} is {}".format(member_id, card))
        canceled = self._label("Canceled", board_name)
        logger.debug("Canceled tag is {}".format(canceled))
        if card:
            card.add_label(canceled)
        logger.debug("cancel_rsvp", self._member.cache_info())
        logger.debug("cancel_rsvp", self._label.cache_info())

    def tables(self, board_name):
        tables = {}
        board = self._board(board_name)
        non_table_list = ["RSVPs", "In Chat (No Group)"]
        info_card = None
        if not board:
            return None
        table_list = [t for t in board.list_lists() if t.name not in non_table_list]
        for table in table_list:
            names = []
            title = table.name
            for card in table.list_cards():
                if card.name != "Info" and not card.labels:
                    names.append(card.name)
                elif card.name == "Info":
                    info_card = card
                elif card.labels:
                    for label in card.labels:
                        if label.name == "GM":
                            names.append(card.name + " (GM)")
                        else:
                            names.append(card.name)
            if info_card:
                info = info_card.desc
            else:
                info = ""
            tables[title] = {}
            tables[title]["members"] = names
            tables[title]["info"] = info
        return tables

    def table(self, board_name, list_name):
        return self.tables(board_name)[list_name]

    @lru_cache(maxsize=128)
    def addressbook_entry_by_name(self, member_name):
        board = self._board("Address Book")
        for l in board.list_lists():
            for card in l.list_cards():
                if card.name == member_name:
                    return yaml.load(card.desc)

    @lru_cache(maxsize=128)
    def addressbook_entry_by_id(self, member_id):
        board = self._board("Address Book")
        for l in board.list_lists():
            for card in l.list_cards():
                info = yaml.load(card.desc)
                if info:
                    if info['id'] == member_id:
                        return info
