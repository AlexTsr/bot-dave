from collections import OrderedDict
from os import environ
from typing import Optional, Dict, List, Set

import requests

from dave.data_types import GameTable, Board, Player
from dave.exceptions import NoBoardError
# from dave.log import logger


# TODO: Split the Trello parts into another class
# TODO: Add logging
# TODO: Documentation


class TableManifest:
    """Connect to tables through https://developers.trello.com/reference/"""

    def __init__(self, api_key: str, token: str) -> None:
        self.base_url = "https://api.trello.com/1/"
        self.payload = {"key": api_key, "token": token}
        self._org_id = None

    def _get(self, path: str, params: Optional[dict] = None) -> List[dict]:
        payload = {**self.payload, **params} if params else self.payload
        url = self.base_url + path
        response = requests.get(url, params=payload)
        if response.ok:
            return response.json()
        else:
            raise ValueError(f"Trello response: {response.text} ({response.status_code})")

    def _post(self, path: str, params: dict) -> bool:
        payload = {**self.payload, **params} if params else self.payload
        url = self.base_url + path
        response = requests.request("POST", url, params=payload)
        return response.ok

    def _delete(self, path: str) -> bool:
        url = self.base_url + path
        response = requests.delete(url, params=self.payload)
        return response.ok

    @property
    def org_id(self) -> Optional[str]:
        if not self._org_id:
            orgs = self._get("/members/me/organizations", {"filter": "all", "fields": "id,name"})
            for org in orgs:
                if org["name"] == environ.get("TRELLO_TEAM"):
                    self._org_id = org["id"]
        return self._org_id

    def _label_id_of(self, label_name: str, board_name: str) -> Optional[str]:
        labels = self._labels_of(board_name)
        label = [l for l in labels if l["name"] == label_name]
        if label:
            return label[0]["id"]
        return None

    @property
    def event_boards(self) -> List[Board]:
        response = self._get("members/me/boards", params={"filter": "open", "lists": "open"})
        return [Board(name=it["name"], board_id=it["id"], org_id=it["idOrganization"], url=it["url"], lists=it["lists"])
                for it in response
                if it["idOrganization"] == self.org_id]

    def _board_id_of(self, board_name: str) -> str:
        return self.board(board_name).id

    # TODO: Narrow down the Exception; only check for "that label is already on the card" exceptions
    def _add_label(self, label_name: str, card_id: str, board_name: str) -> None:
        """https://developers.trello.com/v1.0/reference#cardsididlabels
        """
        label_id = self._label_id_of(label_name, board_name)
        if not label_id:
            return None
        payload = {"value": label_id}
        try:
            self._post(f"cards/{card_id}/idLabels", payload)
        except Exception as e:
            print(e)
            pass

    def _listid_of(self, list_name: str, board_name: str) -> Optional[List[str]]:
        lists = self.board(board_name).lists
        for lst in lists:
            if lst["name"] == list_name:
                return lst["id"]
        return None

    def _card_id_of(self, member_id: int, board_name: str) -> Optional[str]:
        for card in self.cards(board_name):
            if card["desc"] == str(member_id):
                return card["id"]
        return None

    def _add_card(self, card_name: str, desc: str, list_name: str, board_name: str) -> bool:
        list_id = self._listid_of(list_name, board_name)
        payload = {"name": card_name, "desc": desc, "pos": "bottom", "idList": list_id}
        return self._post("cards", payload)

    def board(self, board_name: str) -> Board:
        for board in self.event_boards:
            if board.name == board_name:
                return board
        raise NoBoardError

    def table_list(self, board_name: str) -> Dict[str, GameTable]:
        lists = self.board(board_name).lists
        tables = {}
        for table in lists:
            table_number, table_name = 9999, "Without a Table :disappointed:"
            if table["name"] != "RSVPed":
                table_number, table_name = table["name"].split(". ", 1)
            tables[table["id"]] = GameTable(number=table_number, title=table_name)
        return tables

    def cards(self, board_name: str) -> List[dict]:
        """ https://developers.trello.com/v1.0/reference#boardsboardidcardsfilter
        :param board_name:
        :return:
        """
        board_id = self._board_id_of(board_name)
        path = f"boards/{board_id}/cards/visible"
        return self._get(path)

    def participants_of(self, event_name: str) -> Set[int]:
        resp: Set[int] = set()
        for t in self.tables_for_event(event_name).values():
            if t.player_ids:
                resp |= t.player_ids
                if t.gm.meetup_id:
                    resp.add(t.gm.meetup_id)
        return resp

    def tables_for_event(self, event_name: str) -> Dict[int, GameTable]:
        entries = self.cards(event_name)
        tables = self.table_list(event_name)
        for entry in entries:
            list_id = entry["idList"]
            table = tables[list_id]
            if entry["name"].lower() == "info":
                blurb, max_players = entry["desc"].rsplit("Players: ", 1)
                table.blurb = blurb
                try:
                    table.max_players = int(max_players)
                except ValueError:
                    pass
            elif entry["labels"]:
                for label in entry["labels"]:
                    if label["name"] == "GM":
                        table.gm = Player(entry["name"], int(entry["desc"]))
                    else:
                        table.add_player(Player(f"{entry['name']} ({label['name']})", int(entry["desc"])))
            else:
                table.add_player(Player(entry["name"], int(entry["desc"])))
        tables_by_number = {v.number: v for v in tables.values()}
        return OrderedDict(sorted(tables_by_number.items()))

    def create_event_board(self, board_name: str) -> bool:
        if not self.board(board_name):
            template = self._board_id_of("Meetup Template")
            payload = {"name": board_name, "defaultLabels": "true", "defaultLists": "false", "keepFromSource": "cards",
                       "idBoardSource": template, "prefs_permissionLevel": "org", "prefs_voting": "disabled",
                       "prefs_comments": "members", "prefs_invitations": "members", "prefs_selfJoin": "true",
                       "prefs_cardCovers": "true", "prefs_background": "blue", "prefs_cardAging": "regular",
                       "idOrganization": self.org_id, }
            return self._post("boards", payload)
        return True

    def add_participant(self, name: str, member_id: int, event_name: str) -> None:
        if member_id not in self.participants_of(event_name) and member_id not in self.waitlist_of(event_name):
            self._add_card(name, str(member_id), "RSVPed", event_name)
        elif member_id in self.waitlist_of(event_name):
            self.remove_from_waitlist(member_id, event_name)

    def cancel_rsvp(self, member_id: int, board_name: str) -> None:
        card_id = self._card_id_of(member_id, board_name)
        if card_id:
            self._add_label("Canceled", card_id, board_name)

    def table(self, board_name: str, table_number: int) -> GameTable:
        return self.tables_for_event(board_name)[table_number]

    # TODO
    def add_table(self, title, info, board_url):
        raise NotImplementedError

    def add_to_waitlist(self, member_name: str, member_id: int, event_name: str) -> None:
        self.add_participant(member_name, member_id, event_name)
        card_id = self._card_id_of(member_id, event_name)
        if card_id:
            self._add_label("Waitlist", card_id, event_name)

    def _labels_of(self, board_name: str) -> List[dict]:
        board_id = self._board_id_of(board_name)
        return self._get(f"boards/{board_id}/labels")

    def waitlist_of(self, event_name: str) -> Set[int]:
        wl = set()
        for t in self.tables_for_event(event_name).values():
            for player in t.players:
                if player.name.endswith("(Waitlist)"):
                    wl.add(player.meetup_id)
        return wl

    def remove_from_waitlist(self, member_id: int, event_name: str) -> None:
        card_id = self._card_id_of(member_id, event_name)
        if card_id:
            self._remove_label("Waitlist", card_id, event_name)

    def _remove_label(self, label_name: str, card_id: str, board_name: str) -> None:
        """ https://developers.trello.com/v1.0/reference#cardsididlabelsidlabel
        :param label_name:
        :param card_id:
        :param board_name:
        """
        label_id = self._label_id_of(label_name, board_name)
        if not label_id:
            return
        self._delete(f"cards/{card_id}/idLabels/{label_id}")

    def _labels(self, card_id):
        return self._get(f"cards/{card_id}/labels")
