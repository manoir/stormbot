"""Picked volunteer for stormbot"""
import math
import isodate
import datetime
import random

from .bot import Plugin

class Volunteer:
    def __init__(self, name, role):
        self.name = name
        self.role = role

        now = datetime.datetime.now()
        self.start = role.last_start()

    def remaining(self):
        now = datetime.datetime.now()
        return self.start + self.role.duration - now

class Role:
    def __init__(self, name, start, duration):
        self.name = name
        self.start = start
        self.duration = duration

    def last_start(self):
        now = datetime.datetime.now()
        return math.floor((now - self.start) / self.duration) * self.duration + self.start

class VolunteerPicker(Plugin):
    def __init__(self, args):
        self.roles = [Role("Grand-Pedestre", isodate.parse_datetime("2017-05-29T00"), isodate.parse_duration("P1W")),
                      Role("Semi-Croustillant", isodate.parse_datetime("2017-05-29T11:45"), isodate.parse_duration("PT24H"))]
        self.volunteers = {}
        random.seed()

    @classmethod
    def argparser(cls, parser):
        pass

    def cmdparser(self, parser, bot):
        subparser = parser.add_parser('whois', bot=bot)
        subparser.set_defaults(command=self.run)
        subparser.add_argument("role", type=str, help="Role to be volunteer for", choices=[role.name for role in self.roles])

    def run(self, bot, msg, parser, args):
        role = next((role for role in self.roles if role.name == args.role))
        if not role in self.volunteers:
            self.pick(bot, role)

        volunteer = self.volunteers[role]
        bot.write("{} is {} for {}".format(volunteer.name, role.name, volunteer.remaining()))

    def pick(self, bot, role):
        volunteers = list(bot.plugin['xep_0045'].getRoster(bot.room))
        volunteers = [volunteer for volunteer in volunteers if volunteer != bot.nick]
        volunteer = random.choice(volunteers)

        self.volunteers[role] = Volunteer(volunteer, role)
