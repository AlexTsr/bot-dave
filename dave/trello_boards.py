from collections import OrderedDict, namedtuple
from os import environ
from typing import List, Optional, Dict

import requests

from dave.data_types import GameTable, Board
from dave.log import logger


class TableManifest:
    """Connect to trello through https://developers.trello.com/reference/"""

    def __init__(self, api_key, token):
        self.base_url = "https://api.trello.com/1/"
        self.payload = {"key": api_key, "token": token}
        self._org_id = None

    def _get(self, path, params=None):
        payload = {**self.payload, **params} if params else self.payload
        url = self.base_url + path
        response = requests.get(url, params=payload)
        return response.json()

    def _post(self, path: str, params: dict) -> bool:
        payload = {**self.payload, **params} if params else self.payload
        url = self.base_url + path
        response = requests.request("POST", url, params=payload)
        return response.ok

    @property
    def org_id(self) -> Optional[str]:
        if not self._org_id:
            orgs = self._get("/members/me/organizations", {"filter": "all", "fields": "id,name"})
            for org in orgs:
                if org["name"] == environ.get("TRELLO_TEAM"):
                    self._org_id = org["id"]
        return self._org_id

    def _label(self, label_name, board_name):
        labels = self._labels_of(board_name)
        label = [l for l in labels if l.name == label_name]
        if label:
            return label[0]

    @property
    def boards(self):
        response =  self._get("members/me/boards", params={"filter": "open", "lists": "open"})
        return [Board(name=it["name"], board_id=it["id"], org_id=it["idOrganization"], url=it["url"], lists=it["lists"])
                for it in response
                if it["idOrganization"] == self.org_id]

    def _board_id_of(self, board_name):
        return self.board(board_name).id

    def _add_label(self, label_name, card, board_name):
        raise NotImplementedError

    def _listid_of(self, list_name, board_name):
        lists = self.board(board_name).lists
        for list in lists:
            if list["name"] == list_name:
                return list["id"]

    def _add_card(self, card_name, desc, list_name, board_name):
        list_id = self._listid_of(list_name, board_name)
        payload = {"name": card_name, "desc": desc, "pos": "bottom", "idList": list_id}
        return self._post("cards", payload)

    def board(self, board_name):
        for board in self.boards:
            if board.name == board_name:
                return board

    def table_list(self, board_name: str) -> Dict[str, GameTable]:
        lists = self.board(board_name).lists
        tables = {}
        for table in lists:
            table_number, table_name = 9999, "Without a Table :disappointed:"
            if table["name"] != "RSVPed":
                table_number, table_name = table["name"].split(". ", 1)
            tables[table["id"]] = GameTable(number=table_number, title=table_name)
        return tables

    def cards(self, board_name: str) -> dict:
        path = "boards/{}/cards/visible".format(self._board_id_of(board_name))
        return self._get(path)

    def participants(self, board_name):
        resp = []
        for t in self.tables_for_event(board_name).values():
            resp += t.player_ids
            if t.gm:
                resp.append(t.gm.id)
        return resp

    def tables_for_event(self, event_name: str) -> Dict[int, GameTable]:
        cards = self.cards(event_name)
        tables = self.table_list(event_name)
        player = namedtuple("Player", "name,id")
        for card in cards:
            list_id = card["idList"]
            table = tables[list_id]
            if card["name"].lower() == "info":
                blurb, max_players = card["desc"].rsplit("Players: ", 1)
                table.blurb = blurb
                try:
                    table.max_players = int(max_players)
                except ValueError:
                    pass
            elif card["labels"]:
                for label in card["labels"]:
                    if label["name"] == "GM":
                        table.gm = player(card["name"], int(card["desc"]))
                    else:
                        table.add_player(player(card["name"], int(card["desc"])))
            else:
                table.add_player(player(card["name"], int(card["desc"])))
        tables_by_number = {v.number: v for v in tables.values()}
        return OrderedDict(sorted(tables_by_number.items()))

    def create_board(self, board_name, team_name=None):
        if not self.board(board_name):
            template = self._board_id_of("Meetup Template")
            payload = {"name": board_name, "defaultLabels": "true", "defaultLists": "false", "keepFromSource": "cards",
                       "idBoardSource": template, "prefs_permissionLevel": "org", "prefs_voting": "disabled",
                       "prefs_comments": "members", "prefs_invitations": "members", "prefs_selfJoin": "true",
                       "prefs_cardCovers": "true", "prefs_background": "blue", "prefs_cardAging": "regular",
                       "idOrganization": self.org_id,}
            return self._post("boards", payload)
        return True

    def add_rsvp(self, name: str, member_id: int, board_name: str) -> bool:
        if member_id in self.participants(board_name):
            return True
        return self._add_card(name, member_id, "RSVPed", board_name)

    def cancel_rsvp(self, member_id: int, board_name: str) -> bool:
        return self._add_label("Canceled", member_id, board_name)

    def table(self, board_name: str, table_number: int) -> GameTable:
        return self.tables_for_event(board_name)[table_number]

    def add_table(self, title, info, board_url):
        raise NotImplementedError

    def add_to_waitlist(self, name, member_id, board_name):
        raise NotImplementedError

    def _labels_of(self, board_name):
        return self._get("boards/{}/labels".format(self._board_id_of(board_name)))


# class TrelloBoard(object):
#     def __init__(self, api_key, token):
#         """Creates a TrelloBoard object
#
#         :param api_key: (str) Your Trello api key https://trello.com/1/appKey/generate
#         :param token:  (str) Your Trello token
#         """
#         self.tc = TrelloClient(api_key=api_key, token=token)
#         logger.debug(self.tc.info_for_all_boards(actions="all"))
#
#     def all(self):
#         return self.tc.info_for_all_boards(actions="all")
#
#     @property
#     def boards(self) -> List[Board]:
#         """All the boards that can be accessed
#
#         :return: (Board) list of Board
#         """
#         return self.tc.list_boards()
#
#     @lru_cache(maxsize=128)
#     def _org_id(self, team_name: str) -> str:
#         """Get the id of a Trello team
#
#         :param team_name:
#         :return:
#         """
#         orgs = self.tc.list_organizations()
#         for org in orgs:
#             if org.name == team_name:
#                 return org.id
#
#     @lru_cache(maxsize=128)
#     def _board(self, board_name):
#         logger.debug("Looking up board {}".format(board_name))
#         board = [b for b in self.boards if b.name == board_name]
#         try:
#             return board[0]
#         except IndexError as e:
#             raise NoBoardError from e
#
#     @lru_cache(maxsize=128)
#     def _board_by_url(self, board_url):
#         board = [b for b in self.boards if b.url == board_url]
#         if board:
#             return board[0]
#
#     @lru_cache(maxsize=128)
#     def _member(self, member_id: int, board_name: str) -> Optional[Card]:
#         member_id = str(member_id)
#         try:
#             board = self._board(board_name)
#         except NoBoardError:
#             return
#
#         for l in board.list_lists(list_filter="open"):
#             for card in l.list_cards():
#                 sleep(0.1)
#                 if card.desc == member_id:
#                     return card
#
#     @lru_cache(maxsize=128)
#     def _label(self, label_name, board_name):
#         board = self._board(board_name)
#         label = [l for l in board.get_labels() if l.name == label_name]
#         if label:
#             return label[0]
#
#     def participants(self, board_name):
#         board = self._board(board_name)
#         members = []
#         for l in board.list_lists(list_filter="open"):
#             for card in l.list_cards():
#                 sleep(0.1)
#                 try:
#                     members.append(int(card.desc))
#                 except ValueError:
#                     pass
#         return members
#
#     def create_board(self, board_name, team_name=None):
#         logger.debug("Checking for board {} on {} team".format(board_name, team_name))
#         template = self._board("Meetup Template")
#         org_id = self._org_id(team_name=team_name)
#         try:
#             self._board(board_name)
#         except NoBoardError:
#             self.tc.add_board(board_name=board_name, source_board=template, organization_id=org_id,
#                               permission_level="public")
#
#     def add_rsvp(self, name, member_id, board_name):
#         logger.debug("Adding rsvp {} to {}".format(name, board_name))
#         try:
#             board = self._board(board_name)
#         except NoBoardError:
#             logger.debug("Board {} not found".format(board_name))
#             return
#
#         if not self._member(member_id, board_name):
#             logger.debug("GuildMember {} does not exist in {}. Adding them.".format(member_id, board_name))
#             rsvp_list = board.list_lists(list_filter="open")[0]
#             logger.debug("RSVP list for {}: {}".format(board_name, rsvp_list))
#             rsvp_list.add_card(name=name, desc=str(member_id))
#
#     def cancel_rsvp(self, member_id, board_name):
#         logger.debug("Canceling RSVP for members id {} at {}".format(member_id, board_name))
#         member_card = self._member(member_id, board_name)
#         logger.debug("Card for member id {} is {}".format(member_id, member_card))
#         canceled = self._label("Canceled", board_name)
#         logger.debug("Canceled tag is {}".format(canceled))
#         if member_card:
#             member_card.add_label(canceled)
#
#     def tables_for_event(self, event_name: str) -> Dict[int, GameTable]:
#         tables = {}
#         info_card = None
#         board = self._board(event_name)
#
#         for board_list in board.list_lists(list_filter="open"):
#             if board_list.name.startswith("RSVP"):
#                 title = "Without a table :disappointed:"
#                 table_number = 9999
#             else:
#                 table_number, title = board_list.name.split(". ", maxsplit=1)
#                 table_number = int(table_number)
#
#             table = GameTable(number=table_number, title=title)
#
#             for card in board_list.list_cards():
#                 sleep(0.1)
#                 if card.name == "Info":
#                     info_card = card
#                 elif card.labels:
#                     for label in card.labels:
#                         if label.name == "GM":
#                             table.gm = card.name
#                 else:
#                     table.add_player_id(card.name)
#
#             if info_card:
#                 full_info = info_card.desc.split("Players: ", 1)
#                 table.blurb = full_info[0]
#                 if len(full_info) == 2:
#                     try:
#                         table.max_players = int(full_info[1])
#                     except ValueError:
#                         pass
#
#             tables[table_number] = table
#         return OrderedDict(sorted(tables.items()))
#
#     def table(self, board_name: str, table_number: int) -> GameTable:
#         return self.tables_for_event(board_name)[table_number]
#
#     def add_table(self, title, info, board_url):
#         board = self._board_by_url(board_url)
#         table_numbers = [int(n.name.split(".", 1)[0]) for n in board.list_lists(list_filter="open") if
#                          n.name[0].isnumeric()]
#         ordinal = max(table_numbers) + 1 if table_numbers else 1
#         title = "{}. {}".format(ordinal, title)
#         table = board.add_list(name=title, pos="bottom")
#         info = "\n\nPlayers:".join(info.split("Players:"))
#         table.add_card("Info", desc=info)
#         return "Table *{}* added to *{}*".format(title, board.name)


if __name__ == '__main__':
    trello_key = environ["TRELLO_API_KEY"]
    trello_token = environ["TRELLO_TOKEN"]
    gt = TableManifest(trello_key, trello_token)
    event_name = "Meetup Template"
    # print(gt.table_list(event_name))
    # print(gt.tables_for_event(event_name))
    # print(gt.cards(event_name))
    # print(gt.org_id)
    # print(gt.create_board("Foo"))
    # print(gt.add_rsvp("bar", 101, "Foo"))
    for board in gt.boards:
        print(board.name)
