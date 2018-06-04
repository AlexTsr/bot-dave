#!/usr/bin/env python

import unittest
from data_types import Event, Member, GameTable, Rsvp


class TestBot(unittest.TestCase):

    def setUp(self):
        self.event = Event(id=249792023, name="January Event", time=1527344911000, status="upcoming", rsvp_limit=40,
                           waitlist_count=10, yes_rsvp_count=40, announced=True,
                           event_url="https://www.example.com/Stockholm-Roleplaying-Guild/events/249792023/",
                           venue={"name": "STORG Clubhouse"})
        self.member = Member(name="Dave", meetup_id=100001, slack_id="u19292")
        self.table = GameTable(number=1, title="Awesome Game", blurb="Long text goes here", max_players=4,
                               players=["Dave", "John", "Jane"], gm="Doe", system="D&D")
        self.rsvp = Rsvp(venue="STORG Clubhouse", response="yes", answers=["My email is foo@example.com"],
                         member={"member_id": 100001, "name": "Dave"})

    def test_gametable_addplayer(self):
        table = self.table
        self.assertEqual(table.players, ["Dave", "John", "Jane"])
        table.add_player("John Doe")
        self.assertEqual(table.players, ["Dave", "John", "Jane", "John Doe"])

    def test_gametable_full_false(self):
        table = self.table
        self.assertFalse(table.is_full)

    def test_gametable_full_true(self):
        table = self.table
        table.add_player("John Doe")
        self.assertTrue(table.is_full)


if __name__ == '__main__':
    unittest.main()
