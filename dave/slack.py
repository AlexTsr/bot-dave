from os import environ
from time import sleep
from slackclient import SlackClient

from dave.log import logger


class Slack(object):
    def __init__(self, slack_token, bot_id):
        """Creates a Slack connection object

        :param slack_token: (str) Your Slack API key
        :param bot_id: (str) The bot's user id
        """
        self.sc = SlackClient(slack_token)
        self.at_bot = "<@" + bot_id + ">"
        self.bot_id = bot_id

    @property
    def _channels(self):
        """Gets all channels

        :return: (list) List of channel objects (dicts)
        """
        return self.sc.api_call("channels.list")["channels"]

    def channel_name(self, channel_id):
        """Get the name of the channel with id :channel_:

        :param channel_id: (str)
        :return: (str) The channel name
        """
        for channel in self._channels:
            if channel["id"] == channel_id:
                return channel["name"]

    def channel_topic(self, channel_id):
        info = self.sc.api_call("channels.info", channel=channel_id)
        if info["ok"]:
            return info["channel"]["topic"]["value"]
        else:
            logger.critical("{}".format(info))
            raise ValueError

    def message(self, content, channel, attachments=None, ts=None):
        """Sends a simple message containing :content: to :channel:

        :param list attachments:
        :param content: (str) The, well, content of the message
        :param channel: (str) The channel where to make the announcement. Needs a leading #
        :return: None
        """
        logger.debug("Sending {} to {}".format(content[0:10], channel))
        if ts:
            self.sc.api_call(
                "chat.postMessage",
                as_user=True,
                channel=channel,
                text=content,
                thread_ts=ts,
                attachments=attachments)
        else:
            self.sc.api_call(
                "chat.postMessage",
                as_user=True,
                channel=channel,
                text=content,
                attachments=attachments)

    def send_attachment(self, message, channel, title=None, colour="#808080", extra_options=None):
        if not extra_options:
            extra_options = {}
        attachment = [{"pretext": title, "color": colour, "text": message, **extra_options}]
        self._announcement(attachment, channel=channel)

    def _announcement(self, attachment, channel="#small_council"):
        self.sc.api_call(
            "chat.postMessage",
            as_user=True,
            channel=channel,
            attachments=attachment
        )

    def _is_im(self, channel_id):
        ims = self.sc.api_call("im.list")["ims"]
        ids = [i["id"] for i in ims]
        return channel_id in ids

    # TODO: return the calling user id as well
    def _parse_slack_output(self, slack_rtm_output):
        """Parse the :slack_rtm_output: received from Slack and return everything after the bot's @-name
        or None if it wasn't directed at the bot.

        :param slack_rtm_output: (str) Slack message to parse
        :return: (tuple) A tuple of the striped message and channel id
        """
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output and self.at_bot in output['text'] and output["user"] != 'USLACKBOT' and output["ts"]:
                    # return text excluding the @ mention, whitespace removed
                    logger.debug(output)
                    command = ' '.join([t.strip() for t in output["text"].split(self.at_bot) if t])
                    return command, output["channel"], output["user"], output["ts"]
                elif output and "channel" in output and "text" in output \
                        and self._is_im(output["channel"]) and output["user"] != self.bot_id and \
                        output["user"] != 'USLACKBOT' and output["ts"]:
                    logger.debug(output)
                    return output["text"], output["channel"], output["user"], output["ts"]
                else:
                    logger.debug(output)
        return None, None, None, None

    def new_event(self, event_name, date, venue, url, channel="#announcements"):
        """
        Announces a new event on :channel: using an attachment
        :param event_name: (str) The event's title
        :param date: (str) The event's date formatted the way we want to be presented
        :param venue: (str) The venue of the event
        :param url: (str) The event's URL. Used to create a hyperlink.
        :param channel: (str) The channel where to make the announcement. Needs a leading #
        :return: None
        """
        text = "{}\n{}".format(date, venue)
        extra_options = {"title": event_name, "title_link": url}
        title = "Woohoo! We've got a new event coming up!"
        self.send_attachment(title=title, message=text, channel=channel, extra_options=extra_options)

    def new_rsvp(self, names, response, event_name, spots, waitlist=0, channel="#dungeon_lab"):
        """Announces a new RSVP on :channel:

        :param waitlist: Number of people on the waiting list
        :param names: The names of the ones that RSVPed
        :param response: "yes" or "no"
        :param event_name: The event's title
        :param spots: The number of spots left
        :param channel: The channel where to make the announcement. Needs a leading #
        :return: None
        """
        colour = "#36a64f" if response == "yes" else "b20000"
        waitlist_msg = "\n{} in the waiting list" if waitlist else ""
        text = "{} replied {} for the {}\n{} spots left{}".format(names, response, event_name, spots, waitlist_msg)
        if response == "waitlist":
            text = "{} joined the waitlist for the {}\n{} in the waitlist".format(names, event_name, waitlist)
        self.send_attachment(title="New RSVP", message=text, colour=colour, channel=channel)

    def rtm(self, queue, read_delay=1):
        """Creates a Real Time Messaging connection to Slack and listens for events
        https://api.slack.com/rtm

        :param queue: (queue) A Multiprocess Queue where it'll put the incoming events
        :param read_delay: (int) How often to check for events. Default: 1s
        :return: None
        """
        if self.sc.rtm_connect():
            logger.info("Slack RTM connected")
            self.message("Reporting for duty!", environ.get("LAB_CHANNEL_ID"))
            while True:
                command, channel, user_id, thread = self._parse_slack_output(self.sc.rtm_read())
                if command and channel and user_id and thread:
                    logger.debug("Command found; text: {}, channel: {}, user_id: {}, thread: {}".format(command, channel, user_id, thread))
                    queue.put((command, channel, user_id, thread))
                sleep(read_delay)

    def userid_info(self, user_id):
        logger.debug("Looking for user {}".format(user_id))
        info = self.sc.api_call(
            "users.info",
            user=user_id
        )
        logger.debug("user info: {}".format(info))
        if info["ok"]:
            return info["user"]
        else:
            logger.warn(info["error"])
