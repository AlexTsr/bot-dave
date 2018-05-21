""" New data types for our special, little needs"""
import json
from typing import List


class Member:
    """
    Class to create Member(name, meetup_id, slack_id, sverok_id, group_id) objects
    """
    def __init__(self, name: str, meetup_id: int, slack_id: str, sverok_id: str, group_id: str) -> None:
        self.name = name
        self.group_id = group_id
        self.sverok_id = sverok_id
        self.slack_id = slack_id
        self.meetup_id = meetup_id

    def __repr__(self):
        return "Member(meetup_id={self.meetup_id}, slack_id={self.slack_id}, sverok_id={self.sverok_id}, group_id={" \
               "self.group_id}) "


class Event:
    """
    Class to create Event() objects
    """
    def __init__(self, id: int, name: str, time: int, status: str, rsvp_limit: int, waitlist_count: int,
                 yes_rsvp_count: int, announced: bool, event_url: str, venue: dict, participants: list = None,
                 **kwargs: dict) -> None:
        self.participants = participants or []
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

    def json(self) -> str:
        """
        Serialize object to JSON
        :return: 
        """
        d = {"event_id": self.event_id,
             "name": self.name,
             "time": self.time,
             "status": self.status,
             "rsvp_limit": self.rsvp_limit,
             "waitlist_count": self.waitlist_count,
             "yes_rsvp_count": self.yes_rsvp_count,
             "announced": self.announced,
             "event_url": self.event_url,
             "venue": self.venue,
             "participants": self.participants}
        return json.dumps(d)

    def __repr__(self):
        return "Event(event_id={self.event_id}, name='{self.name}', time={self.time}, status='{self.status}', " \
               "rsvp_limit={self.rsvp_limit}, waitlist_count={self.waitlist_count}, yes_rsvp_count={" \
               "self.yes_rsvp_count}, announced={self.announced}, event_url='{self.event_url}', " \
               "venue={self.venue}, participants={self.participants})".format_map(vars())


class Rsvp:
    """
    Class to create Rsvp objects
    """
    def __init__(self, venue: str, response: str, answers: List[str], member: dict, **kwargs: dict) -> None:
        self.member = member
        self.answers = answers
        self.response = response
        self.venue = venue
        _ = kwargs


class GameTable:
    """ Class to create GameTable() objects """
    def __init__(self, number: int, title: str, blurb: str = None, max_players: int = None, players: list = None,
                 gm: str = None, system: str = None) -> None:
        self.number = int(number)
        self._players = []
        self.system = system
        self.gm = gm
        self.max_players = max_players
        self.players = players
        self.blurb = blurb
        self.title = title

    def add_player(self, player: int) -> None:
        """ Add a player ID to the table's player list.

        :param player: 
        """
        self.players.append(player)

    @property
    def players(self) -> List[int]:
        """ The player IDs of players joining this table
        :return: list of player IDs
        """
        return self._players

    @players.setter
    def players(self, value):
        if value is None:
            value = []
        self._players = value
