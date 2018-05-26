from collections import OrderedDict
from functools import lru_cache
from typing import List, Optional, Dict

from trello import TrelloClient, Card, Board

from data_types import GameTable
from dave.exceptions import NoBoardError
from dave.log import logger


class TrelloBoard(object):
    def __init__(self, api_key, token):
        """Creates a TrelloBoard object

        :param api_key: (str) Your Trello api key https://trello.com/1/appKey/generate
        :param token:  (str) Your Trello token
        """
        self.tc = TrelloClient(api_key=api_key, token=token)

    @property
    def boards(self) -> List[Board]:
        """All the boards that can be accessed

        :return: (Board) list of Board
        """
        return self.tc.list_boards()

    @lru_cache(maxsize=128)
    def _org_id(self, team_name: str) -> str:
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
        logger.debug("Looking up board {}".format(board_name))
        board = [b for b in self.boards if b.name == board_name]
        try:
            return board[0]
        except IndexError as e:
            raise NoBoardError from e

    @lru_cache(maxsize=128)
    def _board_by_url(self, board_url):
        board = [b for b in self.boards if b.url == board_url]
        if board:
            return board[0]

    @lru_cache(maxsize=128)
    def _member(self, member_id: int, board_name: str) -> Optional[Card]:
        member_id = str(member_id)
        try:
            board = self._board(board_name)
        except NoBoardError:
            return

        for l in board.list_lists(list_filter="open"):
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
        logger.debug("Checking for board {} on {} team".format(board_name, team_name))
        template = self._board("Meetup Template")
        org_id = self._org_id(team_name=team_name)
        try:
            self._board(board_name)
        except NoBoardError:
            self.tc.add_board(board_name=board_name, source_board=template, organization_id=org_id,
                              permission_level="public")

    def add_rsvp(self, name, member_id, board_name):
        logger.debug("Adding rsvp {} to {}".format(name, board_name))
        try:
            board = self._board(board_name)
        except NoBoardError:
            logger.debug("Board {} not found".format(board_name))
            return

        if not self._member(member_id, board_name):
            logger.debug("Member {} does not exist in {}. Adding them.".format(member_id, board_name))
            rsvp_list = board.list_lists(list_filter="open")[0]
            logger.debug("RSVP list for {}: {}".format(board_name, rsvp_list))
            rsvp_list.add_card(name=name, desc=member_id)

    def cancel_rsvp(self, member_id, board_name):
        logger.debug("Canceling RSVP for members id {} at {}".format(member_id, board_name))
        member_card = self._member(member_id, board_name)
        logger.debug("Card for member id {} is {}".format(member_id, member_card))
        canceled = self._label("Canceled", board_name)
        logger.debug("Canceled tag is {}".format(canceled))
        if member_card:
            member_card.add_label(canceled)

    def tables_for_event(self, event_name: str) -> Dict[int, GameTable]:
        tables = {}
        info_card = None
        board = self._board(event_name)

        for board_list in board.list_lists(list_filter="open"):
            if board_list.name.startswith("RSVP"):
                title = "Without a table :disappointed:"
                table_number = 9999
            else:
                table_number, title = board_list.name.split(". ", maxsplit=1)
                table_number = int(table_number)

            table = GameTable(number=table_number, title=title)

            for card in board_list.list_cards():
                if card.name == "Info":
                    info_card = card
                elif card.labels:
                    for label in card.labels:
                        if label.name == "GM":
                            table.gm = card.name
                else:
                    table.add_player(card.name)

            if info_card:
                full_info = info_card.desc.split("Players: ", 1)
                table.blurb = full_info[0]
                if len(full_info) == 2:
                    try:
                        table.max_players = int(full_info[1])
                    except ValueError:
                        pass

            tables[table_number] = table
        return OrderedDict(sorted(tables.items()))

    def table(self, board_name: str, table_number: int) -> GameTable:
        return self.tables_for_event(board_name)[table_number]

    def add_table(self, title, info, board_url):
        board = self._board_by_url(board_url)
        table_numbers = [int(n.name.split(".", 1)[0]) for n in board.list_lists(list_filter="open") if
                         n.name[0].isnumeric()]
        ordinal = max(table_numbers) + 1 if table_numbers else 1
        title = "{}. {}".format(ordinal, title)
        table = board.add_list(name=title, pos="bottom")
        info = "\n\nPlayers:".join(info.split("Players:"))
        table.add_card("Info", desc=info)
        return "Table *{}* added to *{}*".format(title, board.name)
