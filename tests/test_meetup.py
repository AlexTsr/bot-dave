#!/usr/bin/env python

import unittest
from unittest import mock

import dave
from meetup import MeetupGroup

# TODO: docstrings
class TestMeetup(unittest.TestCase):

    def setUp(self):
        self.api_key = "dummykey"
        self.group_id = 100
        self.event_id = "123"
        self.meetup = MeetupGroup(self.api_key, self.group_id)
        self._get_events = [{"utc_offset": 7200000,
                             "venue": {"country": "se",
                                       "localized_country_name": "Sweden",
                                       "city": "Stockholm",
                                       "address_1": "Foovägen",
                                       "name": "STORG Clubhouse",
                                       "lon": 28.00798,
                                       "id": 504,
                                       "lat": 79.287373,
                                       "repinned": False
                                       },
                             "rsvp_limit": 40,
                             "waitlist_count": 0,
                             "description": "...",
                             "how_to_find_us": "...",
                             "event_url": "https://www.example.com/Stockholm-Roleplaying-Guild/events/24979/",
                             "yes_rsvp_count": 38,
                             "name": "STORG Awesome Session!",
                             "id": "24979",
                             "time": 1529145000000,
                             "announced": False,
                             "status": "upcoming"
                             }]
        self._get_rsvps = [{"venue": {"country": "se",
                                      "localized_country_name": "Sweden",
                                      "city": "Stockholm",
                                      "address_1": "Folkparksvägen",
                                      "name": "STORG Clubhouse",
                                      "lon": 18.00778,
                                      "id": 24970504,
                                      "lat": 59.287373,
                                      "repinned": False
                                      },
                            "response": "yes",
                            "answers": ["rasmus.thornqvist@gmail.com"],
                            "guests": 0,
                            "member": {"member_id": 208412800, "name": "Rasmus"},
                            },
                           {"venue": {"country": "se",
                                      "localized_country_name": "Sweden",
                                      "city": "Stockholm",
                                      "address_1": "Folkparksvägen",
                                      "name": "STORG Clubhouse",
                                      "lon": 18.00778,
                                      "id": 24970504,
                                      "lat": 59.287373,
                                      "repinned": False
                                      },
                            "response": "yes",
                            "answers": [""],
                            "member": {"member_id": 188666822, "name": "grainne"},
                            },]

    def test_upcoming_events_get(self):
        params = {"key": self.api_key, "group_id": self.group_id, "status": "upcoming"}
        with mock.patch.object(self.meetup, '_get', return_value=self._get_events) as method:
            # noinspection PyStatementEffect
            self.meetup.upcoming_events
            method.assert_called_once_with("/2/events", params)

    def test_upcoming_events(self):
        with mock.patch.object(self.meetup, '_get', return_value=self._get_events):
            events = self.meetup.upcoming_events
            self.assertIsInstance(events, list)
            self.assertIsInstance(events[0], dave.data_types.Event)

    def test_next_event(self):
        with mock.patch.object(self.meetup, '_get', return_value=self._get_events):
            next_event = self.meetup.next_event
            self.assertIsInstance(next_event, dave.data_types.Event)
            self.assertEqual(next_event.name, self._get_events[0]["name"])

    def test_event_names(self):
        with mock.patch.object(self.meetup, '_get', return_value=self._get_events):
            self.assertEqual(self.meetup.event_names, ["STORG Awesome Session!"])

    def test_rsvps_get(self):
        params = {"event_id": self.event_id, "key": self.api_key}
        with mock.patch.object(self.meetup, '_get', return_value=self._get_rsvps) as method:
            self.meetup.rsvps(self.event_id)
            method.assert_called_once_with("/2/rsvps", params)

    def test_rsvps_type(self):
        with mock.patch.object(self.meetup, '_get', return_value=self._get_rsvps) as method:
            rsvps = self.meetup.rsvps(self.event_id)
            self.assertIsInstance(rsvps, list)
            self.assertIsInstance(rsvps[0], dave.data_types.Rsvp)


if __name__ == '__main__':
    unittest.main()
