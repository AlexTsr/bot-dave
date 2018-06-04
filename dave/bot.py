#!/usr/bin/env python

import json
import random
from datetime import datetime, timezone, timedelta
from os import environ
from time import sleep

from fuzzywuzzy import process

from dave.data_types import Event
from dave.log import logger
from dave.meetup import MeetupGroup
from dave.slack import Slack
from dave.trello_boards import TableManifest
from dave.exceptions import NoBoardError

sleep_time = int(environ.get('CHECK_TIME', '600'))


class Bot(object):
    def __init__(self):
        meetup_key = environ.get('MEETUP_API_KEY')
        group_id = environ.get('MEETUP_GROUP_ID')
        slack_token = environ["SLACK_API_TOKEN"]
        trello_key = environ["TRELLO_API_KEY"]
        trello_token = environ["TRELLO_TOKEN"]
        bot_id = environ.get("BOT_ID")
        self.lab_channel_id = environ.get("LAB_CHANNEL_ID")
        self.team_name = environ["TRELLO_TEAM"]
        self.storg = MeetupGroup(meetup_key, group_id)
        self.chat = Slack(slack_token, bot_id)
        self.trello = TableManifest(api_key=trello_key, token=trello_token)
        with open("dave/resources/phrases.json", "r") as phrases:
            self._phrases = json.loads(phrases.read())

    def _handle_event(self, event: Event):
        # Check for new event
        event_names = [b.name for b in self.trello.boards]
        if event.name not in event_names:
            logger.info("New event found: {}".format(event.name))
            self.chat.message("Woohoo! We've got a new event coming up! :party_parrot:\n{}".format(event.event_url),
                              channel="#announcements")
            self.trello.create_board(event.name, team_name=self.team_name)

    def _handle_rsvps(self, event: Event):
        event_name = event.name
        venue = event.venue["name"]
        channel_for_venue = {"STORG Clubhouse": "#storg-south", "STORG Northern Clubhouse": "#storg-north"}
        channel = channel_for_venue.get(venue)
        newcomers = []
        cancels = []
        waitlist_names = []
        newcomer_names = []
        cancel_names = []
        spots_left = int(event.rsvp_limit) - int(event.yes_rsvp_count) if event.rsvp_limit else 'Unknown'

        for rsvp in self.storg.rsvps(event.event_id):
            member_name = rsvp.member["name"]
            member_id = rsvp.member["member_id"]
            known_participants = self.trello.participants(event.name)

            if member_id not in known_participants and rsvp.response == "yes":
                self.trello.add_rsvp(name=member_name, member_id=member_id, board_name=event_name)
                newcomers.append(member_id)
                newcomer_names.append(member_name)
            elif member_id in known_participants and rsvp.response == "no":
                self.trello.cancel_rsvp(member_id, board_name=event_name)
                cancels.append(member_id)
                cancel_names.append(member_name)
            elif rsvp.response == "waitlist":
                waitlist_names.append(member_name)

        if cancel_names:
            self.chat.new_rsvp(', '.join(cancel_names), "no", event_name, spots_left, event.waitlist_count, channel)
        if newcomer_names:
            self.chat.new_rsvp(', '.join(newcomer_names), "yes", event_name, spots_left, event.waitlist_count, channel)

    def _check_for_greeting(self, sentence):
        """If any of the words in the user's input was a greeting, return a greeting response"""
        greeting_keywords = self._phrases["requests"]["greetings"]
        greeting_responses = self._phrases["responses"]["greetings"]
        word = sentence.split(' ')[0]
        if word.lower().rstrip('!') in greeting_keywords:
            return random.choice(greeting_responses)

    @staticmethod
    def _natural_join(lst, separator=None):
        if not separator:
            separator = '\n'
        resp = ',{}'.format(separator).join(lst)
        resp = ' and'.join(resp.rsplit(',', 1))
        return resp

    def _next_event_info(self):
        try:
            next_event = self.storg.next_event
            event_time = next_event.time / 1000
            date = datetime.fromtimestamp(event_time).strftime('%A %B %d at %H:%M')
            name = next_event.name
            msg = "Our next event is *{}* on {}. Info and RSVP at {}".format(name, date, next_event.event_url)
        except IndexError:
            msg = "I can't find any event :disappointed:"
        return msg

    def _all_events_info(self):
        intro = ["Here are our next events.\n"]
        msgs = []
        for event in self.storg.upcoming_events:
            event_time = event.time / 1000
            date = datetime.fromtimestamp(event_time).strftime('%A %B %d at %H:%M')
            name = event.name
            msg = "*{}*, on {}. Info and RSVP at {}".format(name, date, event.event_url)
            msgs.append(msg)
        if msgs:
            return '\n\n'.join(intro + msgs)

    def _tables_info(self, channel, request=None, detail=False, only_available=False, table_number=None):
        logger.debug("Got {} and {}".format(channel, request))
        if not request and channel:
            request = ' '.join(channel.split("_"))

        logger.debug("Request {}".format(request))
        logger.debug("Channel {}".format(channel))
        events = self.storg.event_names
        logger.debug("Events {}".format(events))
        event_name = process.extractOne(request, events)[0]
        logger.debug("Chose {}".format(event_name))

        try:
            tables_for_event = self.trello.tables_for_event(event_name)
        except NoBoardError:
            return "I didn't find anything :disappointed:"

        tables = []

        for table in tables_for_event.values():
            color = "b20000" if table.is_full else "#36a64f"
            title = None
            if only_available and table.is_full:
                continue

            if table_number and table.number != table_number:
                continue

            if detail and table.number != 9999:
                table_title = "{}. {}".format(table.number, table.title)
                text = table.blurb
                joining = "*GM:* {}; *Joining ({} out of {} max):* {}".format(table.gm.name, len(table.players),
                                                                              table.max_players,
                                                                              self._natural_join(table.player_names, ' '))
            elif table.number != 9999:
                table_title = "{}. {}".format(table.number, table.title)
                text = "_Ask *table {}* to get details for this table " \
                       "or *detailed table status* to get details for all tables_".format(table.number)
                joining = "*GM:* {}; *Joining ({} out of {} max):* {}".format(table.gm, len(table.players), table.max_players,
                                                                              self._natural_join(table.player_names, ' '))
            else:
                table_title = table.title
                text = ""
                color = ""
                joining = "*{} left:* {}".format(len(table.players), self._natural_join(table.player_names, ' '))

            attachment = {
                "title": table_title,
                "text": text,
                "color": color,
                "short": True,
                "fields": [{"title": title, "value": joining}],
                "mrkdwn_in": ["text", "pretext", "fields"]
            }
            tables.append(attachment)
        return json.dumps(tables)

    def check_events(self):
        logger.info("Checking for event updates")
        for event in self.storg.upcoming_events:
            self._handle_event(event)
            self._handle_rsvps(event)
        logger.info("Done checking")

    def monitor_events(self, sleep_for=900):
        while True:
            try:
                self.check_events()
            except Exception as e:
                self.chat.message("Swallowed exception at check_events: {}".format(e), self.lab_channel_id)
                logger.error("Swallowed exception at check_events: {}".format(e))
                raise e
            sleep(sleep_for)

    def read_chat(self, tasks):
        self.chat.rtm(tasks)

    def respond(self, response, channel, attachments=None, thread=None):
        self.chat.message(content=response, channel=channel, attachments=attachments, ts=thread)

    def table(self, event_name, table_title):
        return self.trello.table(event_name, table_title)

    def conversation(self, task_queue):
        unknown_responses = self._phrases["responses"]["unknown"]
        while True:
            try:
                command, channel_id, user_id, thread = task_queue.get()
                attachments = None
                if command.startswith("help"):
                    response = "Hold on tight, I'm coming!\nJust kidding!\n\n{}".format(
                        self._phrases["responses"]["help"])
                    thread = None
                elif command.lower().startswith("table status"):
                    response = "Open tables"
                    attachments = self._tables_info(channel=self.chat.channel_name(channel_id),
                                                    request=command.split('table status')[-1], only_available=False)
                elif command.lower().startswith("available tables"):
                    response = "Available tables"
                    attachments = self._tables_info(channel=self.chat.channel_name(channel_id),
                                                    request=command.split('available tables')[-1], only_available=True)
                elif command.lower().startswith("detailed table status"):
                    response = "Available tables"
                    attachments = self._tables_info(channel=self.chat.channel_name(channel_id),
                                                    request=command.split('table status')[-1], detail=True,
                                                    only_available=False)
                elif command.lower().startswith("table"):
                    full_req = command.split('table')[-1].strip()
                    split_req = full_req.split(" ", 1)
                    table_number = int(split_req[0])
                    if len(split_req) == 2:
                        request = split_req[1]
                    else:
                        request = None
                    logger.debug("Table {}".format(table_number))
                    response = "Details for table {}".format(table_number)
                    attachments = self._tables_info(channel=self.chat.channel_name(channel_id),
                                                    request=request, detail=True, table_number=table_number)
                elif "next event" in command.lower() and "events" not in command.lower():
                    response = self._next_event_info()
                    thread = None
                elif "events" in command.lower():
                    thread = None
                    response = self._all_events_info()
                elif "thanks" in command.lower() or "thank you" in command.lower():
                    thread = None
                    response = random.choice(self._phrases["responses"]["thanks"])
                elif command.lower().startswith("what can you do") or command.lower() == "man":
                    thread = None
                    response = self._phrases["responses"]["help"]
                elif "admin info" in command.lower():
                    response = self._phrases["responses"]["admin_info"]
                elif "add table" == command.lower():
                    response = "Sure thing. Just send me a message in the following format:\n" \
                               "add table <TABLE TITLE>: <BLURB>, Players: <MAX NUMBER OF PLAYERS>, e.g.\n" \
                               "```add table Rat Queens (Fate): One more awesome Rat Queens adventure, Players: 5```"
                elif command.lower().startswith("add table"):
                    response = self._add_table(command, channel_id)
                else:
                    thread = None
                    response = self._check_for_greeting(command) if self._check_for_greeting(
                        command) else random.choice(
                        unknown_responses)
                self.respond(response, channel_id, attachments=attachments, thread=thread)
            except Exception as e:
                self.chat.message("Swallowed exception at conversation: {}".format(e), self.lab_channel_id)
                logger.error("Swallowed exception at conversation: {}".format(e))
                raise e

    def _add_table(self, command, channel_id):
        title, info = command.split(":", 1)
        title = title.split("add table")[-1]
        try:
            board_url = self.chat.channel_topic(channel_id).strip("<").strip(">")
        except ValueError:
            return "I can't find the Trello board for this channel." \
                   " Make sure the topic of this channel is the URL of the event's Trello board"
        return self.trello.add_table(title, info, board_url)
