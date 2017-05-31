"""Picked volunteer for stormbot"""
import math
import isodate
import datetime
import random
import pickle

from .bot import Plugin

class Volunteer:
    def __init__(self, name, role):
        self.name = name
        self.role = role

    def appoint(self):
        return Actor(self)

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash((self.name, self.role))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and (self.name, self.role) == (other.name, other.role)

    def __ne__(self, other):
        return not (self == other)

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

    def __hash__(self):
        return hash((self.volunteer, self.start))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and (self.volunteer, self.start) == (other.volunteer, other.start)

    def __ne__(self, other):
        return not (self == other)

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

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    def __ne__(self, other):
        return not (self == other)

class VolunteerPicker(Plugin):
    def __init__(self, bot, args):
        self._bot = bot
        self.args = args
        self.roles = []
        for index, role in enumerate(args.volunteer_role):
            self.roles.append(Role(role, args.volunteer_role_start[index], args.volunteer_role_duration[index]))
        self.actors = {}
        if self.args.volunteer_all:
            roster = list(self._bot.plugin['xep_0045'].getRoster(self._bot.room))
            self.volunteers = {role: [Volunteer(name, role) for name in roster if name != self._bot.nick]
                               for role in self.roles}
        else:
            self.volunteers = {role: [] for role in self.roles}

        try:
            with open(self.args.volunteer_cache, 'rb') as cache:
                cache = pickle.load(cache)
            if "actors" in cache:
                for cached_role, cached_actor in cache["actors"].items():
                    if cached_role in self.roles:
                        self.actors[cached_role] = cached_actor
        except (IOError, pickle.PickleError):
            pass

        random.seed()

        for role in self.roles:
            self.write_volunteers(role)

    def got_online(self, presence):
        if self.args.volunteer_all:
            for role in self.roles:
                self.volunteers[role].append(Volunteer(presence['muc']['nick'], role))

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
        parser.add_argument("--volunteer-all", action='store_true', default=False, help="Consider all participants as volunteers")
        parser.add_argument("--volunteer-cache", type=str, default="/var/cache/stormbot/volunteer.p", help="Cache file (default: %(default)s)")
        parser.add_argument("--volunteer-role", type=str, action='append')
        parser.add_argument("--volunteer-role-start", type=isodate.parse_datetime, action='append')
        parser.add_argument("--volunteer-role-duration", type=isodate.parse_duration, action='append')

    def role(self, rolename):
        return next((role for role in self.roles if role.name == rolename), rolename)

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
        if not args.role in self.actors or self.actors[args.role].remaining < datetime.timedelta(0):
            if len(self.volunteers[args.role]) < 1:
                self._bot.write("nobody is willing to be {}".format(args.role))
                return

            self.pick(random.choice(self.volunteers[role]))

        self.write_actors(args.role)

    def iam(self, msg, parser, args):
        volunteer = Volunteer(msg['mucnick'], args.role)
        if volunteer not in self.volunteers[args.role]:
            self.volunteers[args.role].append(volunteer)
        self._bot.write("{}: thanks !".format(volunteer.name))
        if args.role in self.actors:
            self._bot.write("{}: you are no longer {} thanks to {}".format(self.actors[args.role],
                                                                           args.role,
                                                                           volunteer))
        self.pick(volunteer)
        self.write_actors(args.role)

    def whocouldbe(self, msg, parser, args):
        self.write_volunteers(args.role)

    def icouldbe(self, msg, parser, args):
        volunteer = Volunteer(msg['mucnick'], args.role)
        if volunteer not in self.volunteers[args.role]:
            self.volunteers[args.role].append(volunteer)
            self._bot.write("{}: glad to here that".format(msg['mucnick']))
            self.write_volunteers(args.role)
        else:
            self._bot.write("{}: you already volunteered for {}".format(msg['mucnick'], args.role))

    def pick(self, volunteer):
        self.actors[volunteer.role] = volunteer.appoint()
        try:
            with open(self.args.volunteer_cache, 'wb') as cache:
                pickle.dump({"actors": self.actors}, cache)
        except IOError as err:
            print("can't cache choosen actor: {}".format(err))
