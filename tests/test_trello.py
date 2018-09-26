#!/usr/bin/env python

import unittest
from unittest import mock

# TODO: docstrings
from trello_boards import TableManifest


class TestMeetup(unittest.TestCase):

    def setUp(self):
        self.api_key = "key"
        self.token = "token"
        self.trello = TableManifest(self.api_key, self.token)
        self._get_orgs = ""
        # TODO: anonymize data
        self._get_boards = [{'id': 'fakeid101',
                            'name': 'board101',
                            'desc': '',
                            'descData': None,
                            'closed': False,
                            'idOrganization': 'org100',
                            'invited': False,
                            'url': 'https://example.com/b/dsdiwed/board101',
                            'subscribed': False,
                            'labelNames': {
                                'green': '',
                                'yellow': '',
                                'orange': '',
                                'red': '',
                                'purple': '',
                                'blue': '',
                                'sky': '',
                                'lime': '',
                                'pink': '',
                                'black': ''
                            },
                            'shortUrl': 'https://example.com/b/dsdiwed',
                            'idTags': [],
                            'lists': [
                                {
                                    'id': '5a0ea7cf302082dc308ffb46',
                                    'name': 'Directory',
                                    'closed': False,
                                    'idBoard': '59e5adcdb294c7e7f3d0aac6',
                                    'pos': 32767.5,
                                    'subscribed': False
                                },
                                {
                                    'id': '59e5adfe04f1e01746373f68',
                                    'name': 'Phone Numbers',
                                    'closed': False,
                                    'idBoard': '59e5adcdb294c7e7f3d0aac6',
                                    'pos': 65535,
                                    'subscribed': False
                                }
                            ],
                            },
                            {'id': '59e5adcdb294c7e7f3d0aac6',
                             'name': 'Address Book',
                             'desc': '',
                             'descData': None,
                             'closed': False,
                             'idOrganization': '59da41cd2ff0a3440c843447',
                             'invited': False,
                             'url': 'https://tables.com/b/ZQVnzhxB/address-book',
                             'subscribed': False,
                             'labelNames': {
                                 'green': '',
                                 'yellow': '',
                                 'orange': '',
                                 'red': '',
                                 'purple': '',
                                 'blue': '',
                                 'sky': '',
                                 'lime': '',
                                 'pink': '',
                                 'black': ''
                             },
                             'shortUrl': 'https://tables.com/b/ZQVnzhxB',
                             'idTags': [],
                             'lists': [
                                 {
                                     'id': '5a0ea7cf302082dc308ffb46',
                                     'name': 'Directory',
                                     'closed': False,
                                     'idBoard': '59e5adcdb294c7e7f3d0aac6',
                                     'pos': 32767.5,
                                     'subscribed': False
                                 },
                                 {
                                     'id': '59e5adfe04f1e01746373f68',
                                     'name': 'Phone Numbers',
                                     'closed': False,
                                     'idBoard': '59e5adcdb294c7e7f3d0aac6',
                                     'pos': 65535,
                                     'subscribed': False
                                 }
                             ],
                             },
                            ]
        self._get_cards = ""
        self._get_labels = ""

    def test_upcoming_events_get(self):
        params = {"filter": "open", "lists": "open"}
        with mock.patch.object(self.trello, '_get', return_value=self._get_orgs) as method:
            self.trello.event_boards
            method.assert_called_once_with("members/me/boards", params=params)


if __name__ == '__main__':
    unittest.main()
