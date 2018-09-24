""" New data types for our special, little needs"""
from collections import namedtuple
from typing import List

Player = namedtuple("Player", "name,meetup_id")


class GuildMember:
    """
    Class to create GuildMember(name, meetup_id, slack_id, sverok_id, group_id) objects
    """

    def __init__(
        self,
        name: str,
        meetup_id: int,
        slack_id: str = None,
        sverok_id: str = None,
        group_id: str = None,
    ) -> None:
        self.name = name
        self.group_id = group_id
        self.sverok_id = sverok_id
        self.slack_id = slack_id
        self.meetup_id = meetup_id

    def __repr__(self):
        return f"GuildMember(meetup_id={self.meetup_id}, slack_id={self.slack_id}, sverok_id={self.sverok_id}, " \
               f"group_id={self.group_id})"


class Event:
    """
    Class to create Event() objects
    """

    def __init__(
        self,
        id: str,
        name: str,
        time: int,
        status: str,
        rsvp_limit: int,
        waitlist_count: int,
        yes_rsvp_count: int,
        announced: bool,
        event_url: str,
        venue: dict,
        **kwargs: dict,
    ) -> None:
        self.venue = venue
        self.event_url = event_url
        self.announced = announced
        self.yes_rsvp_count = yes_rsvp_count
        self.waitlist_count = waitlist_count
        self.rsvp_limit = rsvp_limit
        self.status = status
        self.time = time
        self.name = name
        self.event_id = id
        _ = kwargs

    def __repr__(self):
        return f"Event(event_id='{self.event_id}', name='{self.name}', time={self.time}, status='{self.status}', " \
               f"rsvp_limit={self.rsvp_limit}, waitlist_count={self.waitlist_count}, " \
               f"yes_rsvp_count={self.yes_rsvp_count}, announced={self.announced}, event_url='{self.event_url}', " \
               f"venue={self.venue})"


class Rsvp:
    """
    Class to create Rsvp objects
    """

    def __init__(
        self,
        venue: str,
        response: str,
        answers: List[str],
        member: dict,
        **kwargs: dict,
    ) -> None:
        self.member = member
        self.answers = answers
        self.response = response
        self.venue = venue
        _ = kwargs


class GameTable:
    """ Class to create GameTable() objects """

    def __init__(
        self,
        number: int,
        title: str,
        blurb: str = None,
        max_players: int = 9999,
        players: List[Player] = None,
        gm: Player = None,
        system: str = None,
    ) -> None:

        self.number = int(number)
        self._players = players or []
        self.system = system
        self.gm = gm or Player(None, None)
        self.max_players = max_players
        self.blurb = blurb
        self.title = title

    def add_player(self, player: Player) -> None:
        """ Add a player name to the table's player list.

        :param player: 
        """
        self.players.append(player)

    @property
    def players(self) -> List[Player]:
        """ The player names of players joining this table
        :return: list of player names
        """
        return self._players

    # @players.setter
    # def players(self, value):
    #     if value is None:
    #         value = []
    #     self._players = value

    @property
    def player_ids(self) -> List[int]:
        return [j for i, j in self.players]

    @property
    def player_names(self):
        return [i for i, j in self.players]

    @property
    def is_full(self):
        return self.max_players == len(self.players)

    def __repr__(self):
        return f"GameTable(number={self.number}, title='{self.title}', blurb='{self.blurb}', " \
               f"max_players={self.max_players}, players={self.players}, gm='{self.gm}', system='{self.system}')"


class Board:
    def __init__(
        self, name: str, board_id: str, org_id: str, url: str, lists: List[dict]
    ) -> None:
        self.lists = lists
        self.url = url
        self.org_id = org_id
        self.id = board_id
        self.name = name

    def __repr__(self):
        return f"Board(name='{self.name}', board_id='{self.id}', org_id='{self.org_id}', lists={self.lists})"
