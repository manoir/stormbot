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

    def appoint(self):
        return Actor(self)

    def __str__(self):
        return self.name

class Actor:
    def __init__(self, volunteer):
        self.volunteer = volunteer
        now = datetime.datetime.now()
        self.start = self.role.last_start()

    @property
    def name(self):
        return self.volunteer.name

    @property
    def role(self):
        return self.volunteer.role

    @property
    def remaining(self):
        now = datetime.datetime.now()
        return self.start + self.role.duration - now

    def __str__(self):
        return self.name

class Role:
    def __init__(self, name, start, duration):
        self.name = name
        self.start = start
        self.duration = duration

    def last_start(self):
        now = datetime.datetime.now()
        return math.floor((now - self.start) / self.duration) * self.duration + self.start

    def __str__(self):
        return self.name

class VolunteerPicker(Plugin):
    def __init__(self, bot, args):
        self._bot = bot
        self.roles = [Role("Grand-Pedestre", isodate.parse_datetime("2017-05-29T00"), isodate.parse_duration("P1W")),
                      Role("Semi-Croustillant", isodate.parse_datetime("2017-05-29T11:45"), isodate.parse_duration("PT24H"))]
        if args.volunteer_all:
            roster = list(self._bot.plugin['xep_0045'].getRoster(self._bot.room))
            self.volunteers = {role: [Volunteer(name, role) for name in roster if name != self._bot.nick]
                               for role in self.roles}
        else:
            self.volunteers = {role: [] for role in self.roles}
        self.actors = {}
        random.seed()

        for role in self.roles:
            self.write_volunteers(role)

    def write_volunteers(self, role):
        volunteers = self.volunteers[role]
        self._bot.write("{} {} for {}".format(", ".join([str(volunteer) for volunteer in volunteers])
                                              if len(volunteers) > 0 else "nobody",
                                              "are volunteers" if len(volunteers) > 1 else "is volunteer",
                                              role.name))

    def write_actors(self, role):
        actor = self.actors[role]
        self._bot.write("{} is {} for {}".format(actor.name, actor.role.name, actor.remaining))

    @classmethod
    def argparser(cls, parser):
        parser.add_argument("--volunteer-all",  action='store_true', default=False, help="Consider all participants as volunteers")

    def role(self, rolename):
        return next((role for role in self.roles if role.name == rolename), None)

    def cmdparser(self, parser):
        subparser = parser.add_parser('whois', bot=self._bot)
        subparser.set_defaults(command=self.whois)
        subparser.add_argument("role", type=self.role, help="Role to be volunteer for", choices=self.roles)
        subparser = parser.add_parser('iam', bot=self._bot)
        subparser.set_defaults(command=self.iam)
        subparser.add_argument("role", type=self.role, help="Role to be volunteer for", choices=self.roles)
        subparser = parser.add_parser('whocouldbe', bot=self._bot)
        subparser.set_defaults(command=self.whocouldbe)
        subparser.add_argument("role", type=self.role, help="Role to be volunteer for", choices=self.roles)
        subparser = parser.add_parser('icouldbe', bot=self._bot)
        subparser.set_defaults(command=self.icouldbe)
        subparser.add_argument("role", type=self.role, help="Role to be volunteer for", choices=self.roles)

    def whois(self, msg, parser, args):
        if not args.role in self.actors:
            self.pick(args.role)

        self.write_actors(args.role)

    def iam(self, msg, parser, args):
        volunteer = Volunteer(msg['mucnick'], args.role)
        self.volunteers[args.role].append(volunteer)
        self._bot.write("{}: thanks !".format(volunteer.name))
        if args.role in self.actors:
            self._bot.write("{}: you are no longer {} thanks to {}".format(self.actors[args.role],
                                                                           args.role,
                                                                           volunteer))
        self.actors[args.role] = volunteer.appoint()
        self.write_actors(args.role)

    def whocouldbe(self, msg, parser, args):
        self.write_volunteers(args.role)

    def icouldbe(self, msg, parser, args):
        volunteer = Volunteer(msg['mucnick'], args.role)
        self.volunteers[args.role].append(volunteer)
        self._bot.write("{}: glad to here that".format(msg['mucnick']))
        self.write_volunteers(args.role)

    def pick(self, role):
        volunteer = random.choice(self.volunteers[role])

        self.actors[role] = volunteer.appoint()
