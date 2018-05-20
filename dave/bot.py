#!/usr/bin/env python

import json
import random

from datetime import datetime, timezone, timedelta
from os import environ
from time import sleep
from fuzzywuzzy import process

from dave.log import logger
from dave.meetup import MeetupGroup
from dave.slack import Slack
from dave.store import Store
from dave.trello_boards import TrelloBoard
from data_types import Event, Rsvp

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
        self.trello = TrelloBoard(api_key=trello_key, token=trello_token)
        self.ds = Store()
        with open("dave/resources/phrases.json", "r") as phrases:
            self._phrases = json.loads(phrases.read())
        if self.storg.upcoming_events:
            current_event_ids = [e.event_id for e in self.storg.upcoming_events]
            self.stored_events = self.ds.retrieve_events(current_event_ids)
        else:
            self.stored_events = {}

        logger.debug("Known events: {}".format(self.stored_events))
        logger.debug("Env: {}".format(environ.items()))
        self.chat.message("Reporting for duty!", environ.get("LAB_CHANNEL_ID"))

    @property
    def event_names(self):
        return [e["name"] for e in self.stored_events.values()]

    def _handle_event(self, event: Event):
        cet = timezone(timedelta(0, 3600), "CET")
        # Check for new event
        event_id = event.event_id
        if event_id not in self.stored_events.keys():
            logger.info("New event found: {}".format(event.name))
            event_date = int(event.time) / 1000
            event_date = datetime.fromtimestamp(event_date, tz=cet).strftime('%A %B %d %H:%M')

            self.chat.new_event(event.name, event_date, event.venue["name"], event.event_url)
            self.trello.create_board(event.name, team_name=self.team_name)
            self.stored_events[event_id] = event
            # self.stored_events[event_id]["participants"] = []

    def _handle_rsvps(self, event: Event):
        event_id = event.event_id
        event_name = event.name
        venue = event.venue["name"]
        channel_for_venue = {"STORG Clubhouse": "#storg-south", "STORG Northern Clubhouse": "#storg-north"}
        channel = channel_for_venue.get(venue)
        newcomers = []
        newcomer_names = []
        cancels = []
        cancels_names = []

        for rsvp in self.storg.rsvps(event_id):
            member_name = rsvp.member["name"]
            member_id = rsvp.member["member_id"]
            try:
                event = self.stored_events[event_id]
                known_participants = event.participants
            except KeyError:
                logger.error("Event {} not found in stored events".format(event_id))
                logger.error("Known events: {}".format(self.stored_events))
                continue

            if member_name not in known_participants and rsvp.response == "yes":
                self.trello.add_rsvp(name=member_name, member_id=member_id, board_name=event_name)
                newcomers.append(member_name)
                sleep(0.2)
            elif member_name in known_participants and rsvp.response == "no":
                self.trello.cancel_rsvp(member_id, board_name=event_name)
                cancels.append(member_id)
                cancels_names.append(member_name)

        if newcomers or cancels:
            spots_left = int(event.rsvp_limit) - int(event.yes_rsvp_count) if event.rsvp_limit else 'Unknown'

            if cancels:
                logger.info("Cancellations found: {}".format(cancels))
                self.chat.new_rsvp(', '.join(cancels), "no", event_name, spots_left, channel, event.waitlist_count)
                event.participants = [p for p in event.participants if p not in cancels]
                logger.debug("Participant list: {}".format(event.participants))

            if newcomers:
                logger.info("Newcomers found: {}".format(newcomers))
                self.chat.new_rsvp(', '.join(newcomers), "yes", event_name, spots_left, channel, event.waitlist_count)
                event.participants += newcomers
                logger.debug("Participant list: {}".format(event.participants))
        else:
            logger.info("No changes for {}".format(event_name))

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
        next_event = self.next_event
        if next_event:
            participants = next_event["participants"]
            event_time = next_event["time"] / 1000
            date = datetime.fromtimestamp(event_time).strftime('%A %B %d at %H:%M')
            name = next_event["name"]
            msg = "Our next event is *{}*, on *{}* and " \
                  "there are *{}* people joining:\n{}".format(name, date, len(participants),
                                                              self._natural_join(participants))
        else:
            msg = "I can't find any event :disappointed:"
        return msg

    def _all_events_info(self):
        msgs = ["Here are our next events.\n"]
        for event in self.stored_events.values():
            participants = event["participants"]
            event_time = event["time"] / 1000
            date = datetime.fromtimestamp(event_time).strftime('%A %B %d at %H:%M')
            name = event["name"]
            msg = "*{}*,\non *{}* with *{}* " \
                  "people joining:\n{}".format(name, date, len(participants), self._natural_join(participants))
            msgs.append(msg)
        return '\n\n'.join(msgs)

    def _tables_info(self, channel, request=None, detail=False, table_number=None):
        logger.debug("Got {} and {}".format(channel, request))
        if not request and channel:
            request = ' '.join(channel.split("_"))

        logger.debug("Request {}".format(request))
        logger.debug("Channel {}".format(channel))
        events = self.event_names
        logger.debug("Events {}".format(events))
        event_name = process.extractOne(request, events)[0]
        logger.debug("Chose {}".format(event_name))

        table_info = self.trello.tables_detail(event_name)

        tables = []

        for table_number, table in table_info.items():
            color = "b20000" if table.max_players == len(table.players) else "#36a64f"
            if detail and table.number !=0:
                text = table.blurb
                title = "Joining ({} out of {} max)".format(len(table.players), table.max_players)
            elif table_number != 0:
                text = "_Ask *table {}* to get details for this table " \
                       "or *detailed table status* to get details for all tables_".format(table_number)
                title = "Joining ({} out of {} max)".format(len(table.players), table.max_players)
            else:
                text = ""
                title = "{} left".format(len(table.players))
                color = ""

            attachment = {
                "title": table.title.upper(),
                "text": text,
                "color": color,
                "fields": [
                    {"title": title,
                     "value": ', '.join(table.players)}
                ]
            }
            tables.append(attachment)

        return json.dumps(tables)

    def check_events(self):
        logger.info("Checking for event updates")
        for event in self.storg.upcoming_events:
            self._handle_event(event)
            self._handle_rsvps(event)
        logger.info("Done checking")

    def save_events(self):
        logger.debug("Saving events")
        self.ds.store_events(self.stored_events)

    def monitor_events(self, sleep_time=900):
        while True:
            try:
                self.check_events()
            except Exception as e:
                self.chat.message("Swallowed exception at check_events: {}".format(e), self.lab_channel_id)
                logger.error("Swallowed exception at check_events: {}".format(e))
                raise e
            self.save_events()
            sleep(sleep_time)

    def read_chat(self, tasks):
        self.chat.rtm(tasks)

    def respond(self, response, channel, attachments=None):
        self.chat.message(content=response, channel=channel, attachments=attachments)

    # TODO: Move to MeetupGroup
    @property
    def next_event(self):
        if not self.storg.upcoming_events:
            return None
        self.storg.upcoming_events.sort(key=lambda d: d["time"])
        next_id = self.storg.upcoming_events[0]["id"]
        return self.stored_events[next_id]

    def table(self, event_name, table_title):
        return self.trello.table(event_name, table_title)

    def conversation(self, task_queue):
        unknown_responses = self._phrases["responses"]["unknown"]
        while True:
            try:
                command, channel_id, user_id = task_queue.get()
                attachments = None
                if command.startswith("help"):
                    response = "Hold on tight, I'm coming!\nJust kidding!\n\n{}".format(self._phrases["responses"]["help"])
                elif command.lower().startswith("table status"):
                    response = "Available tables"
                    attachments = self._tables_info(channel=self.chat.channel_name(channel_id),
                                                    request=command.split('table status')[-1])
                elif command.lower().startswith("detailed table status"):
                    response = "Available tables"
                    attachments = self._tables_info(channel=self.chat.channel_name(channel_id),
                                                    request=command.split('table status')[-1], detail=True)
                elif command.lower().startswith("table"):
                    full_req = command.split('table')[-1].strip()
                    split_req = full_req.split(" ", 1)
                    table_number = split_req[0]
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
                elif "events" in command.lower():
                    response = self._all_events_info()
                elif "thanks" in command.lower() or "thank you" in command.lower():
                    response = random.choice(self._phrases["responses"]["thanks"])
                elif command.lower().startswith("what can you do") or command.lower() == "man":
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
                    response = self._check_for_greeting(command) if self._check_for_greeting(command) else random.choice(
                        unknown_responses)
                self.respond(response, channel_id, attachments=attachments)
            except Exception as e:
                self.chat.message("Swallowed exception at conversation: {}".format(e), self.lab_channel_id)
                logger.error("Swallowed exception at conversation: {}".format(e))

    def _add_table(self, command, channel_id):
        title, info = command.split(":", 1)
        title = title.split("add table")[-1]
        try:
            board_url = self.chat.channel_topic(channel_id).strip("<").strip(">")
        except ValueError:
            return "I can't find the Trello board for this channel." \
                   " Make sure the topic of this channel is the URL of the event's Trello board"
        return self.trello.add_table(title, info, board_url)
