from collections import OrderedDict, namedtuple
from os import environ
from typing import Optional, Dict

import requests

from dave.data_types import GameTable, Board
# from dave.log import logger


# TODO: Split the Trello parts into another class
# TODO: Add logging
# TODO: Documentation
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
        response = self._get("members/me/boards", params={"filter": "open", "lists": "open"})
        return [Board(name=it["name"], board_id=it["id"], org_id=it["idOrganization"], url=it["url"], lists=it["lists"])
                for it in response
                if it["idOrganization"] == self.org_id]

    def _board_id_of(self, board_name):
        return self.board(board_name).id

    def _add_label(self, label_name, card, board_name):
        raise NotImplementedError

    def _listid_of(self, list_name, board_name):
        lists = self.board(board_name).lists
        for lst in lists:
            if lst["name"] == list_name:
                return lst["id"]

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
                       "idOrganization": self.org_id, }
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
