"""
Main bot of stormbot
"""
import argparse
import shlex

from abc import ABCMeta, abstractmethod
from sleekxmpp import ClientXMPP

class Plugin(metaclass=ABCMeta):
    """Abstract plugin to be subclassed for each command of StormBot"""
    def __init__(self, args=None):
        pass

    @classmethod
    def argparser(cls, parser):
        """Build arg parser for stormbot (run from shell)"""
        pass

    @abstractmethod
    def cmdparser(self, parser, bot):
        """Build command parser for stormbot (in chat)"""
        pass

    @classmethod
    @abstractmethod
    def run(self, bot, msg, parser, args):
        """Run this specific plugin"""
        pass


class Helper(Plugin):
    """Print help"""
    def cmdparser(self, parser, bot):
        print(parser)
        subparser = parser.add_parser('help', bot=bot)
        subparser.set_defaults(command=self.run)

    def run(self, bot, msg, parser, *_):
        bot.write(parser.format_help())


class CommandParserError(Exception):
    def __init__(self, message, usage):
        self.message = message
        self.usage = usage


class CommandParserAbort(Exception):
    pass


class CommandParser(argparse.ArgumentParser):
    def __init__(self, bot=None, **_):
        super().__init__(**_)
        self.bot = bot

    def error(self, message):
        """error(message: string)

        Raise command parser error with usage
        """
        raise CommandParserError(message, self.format_usage())

    def print_help(self, *_):
        self.bot.write(self.format_help())

    def exit(self, status=0, message=None):
        if message:
            self.bot.write(message)
        raise CommandParserAbort(Exception)

class StormBot(ClientXMPP):
    """Storm Bot executing your deepest desires"""
    def __init__(self, jid, password, room, plugins):
        super().__init__(jid, password)
        self.room, _, self.nick = room.partition('/')
        self.nick = self.nick or "stormbot"
        self.plugins = [Helper()] + (plugins or [])

        self.init_parser()

        self.add_event_handler("session_start", self.session_start)

        self.register_plugin('xep_0045') # MUC
        self.add_event_handler("groupchat_message", self.muc_message)

    def init_parser(self):
        self.parser = CommandParser(description="stormbot executing your orders",
                                    prog=self.nick + ':', add_help=False,
                                    bot=self)
        subparsers = self.parser.add_subparsers()
        for plugin in self.plugins:
            plugin.cmdparser(subparsers, self)

    def session_start(self, _):
        """Start an xmpp session"""
        self.send_presence()
        self.plugin['xep_0045'].joinMUC(self.room, self.nick, wait=True)

    def muc_message(self, msg):
        """Handle received message"""
        if msg['mucnick'] != self.nick:
            if msg['body'].startswith(self.nick + ':'):
                try:
                    self.command(msg)
                except CommandParserError as e:
                    self.write(e.message)
                    self.write(e.usage)
            elif msg['body'].startswith('all:'):
                try:
                    self.command(msg)
                except CommandParserError as e:
                    pass

    def command(self, msg):
        """Handle a received command"""
        args = shlex.split(msg['body'])[1:]
        try:
            args = self.parser.parse_args(args)
            args.command(self, msg, self.parser, args)
        except CommandParserAbort:
            pass

    def write(self, string):
        self.send_message(mto=self.room, mbody=string, mtype='groupchat')
