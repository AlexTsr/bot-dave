#!/usr/bin/env python

import unittest
from data_types import Event, GuildMember, GameTable, Rsvp, Player, Board


# TODO: docstrings
class TestDataTypes(unittest.TestCase):

    def setUp(self):
        self.event = Event(id=249792023, name="January Event", time=1527344911000, status="upcoming", rsvp_limit=40,
                           waitlist_count=10, yes_rsvp_count=40, announced=True,
                           event_url="https://www.example.com/Stockholm-Roleplaying-Guild/events/249792023/",
                           venue={"name": "STORG Clubhouse"})
        self.member = GuildMember(name="Dave", meetup_id=100001, slack_id="u19292")
        gm = Player("Maria", 1000)
        dave = Player("Dave", 1001)
        john = Player("John", 1002)
        jane = Player("Jane", 1003)
        self.table = GameTable(number=1, title="Awesome Game", blurb="Long text goes here", max_players=4,
                               players=[dave, john, jane], gm=gm, system="D&D")
        self.rsvp = Rsvp(venue="STORG Clubhouse", response="yes", answers=["My email is foo@example.com"],
                         member={"member_id": 100001, "name": "Dave"})

    def test_gametable_names_addplayer(self):
        jdoe = Player("John Doe", 1004)
        table = self.table
        self.assertEqual(table.player_names, ["Dave", "John", "Jane"])
        table.add_player(jdoe)
        self.assertEqual(table.player_names, ["Dave", "John", "Jane", "John Doe"])

    def test_gametable_ids_addplayer(self):
        jdoe = Player("John Doe", 1004)
        table = self.table
        self.assertEqual(table.player_ids, [1001, 1002, 1003])
        table.add_player(jdoe)
        self.assertEqual(table.player_ids, [1001, 1002, 1003, 1004])

    def test_gametable_full_false(self):
        table = self.table
        self.assertFalse(table.is_full)

    def test_gametable_full_true(self):
        jdoe = Player("John Doe", 1004)
        table = self.table
        table.add_player(jdoe)
        self.assertTrue(table.is_full)

    def test_board_attrs(self):
        b = Board("Test Board", "22033jjdi29sw", "3j3j4osjocvf0", "http://example.com", [{}])
        self.assertEqual(b.lists, [{}])


if __name__ == '__main__':
    unittest.main()
