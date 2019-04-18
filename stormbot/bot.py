"""
Main bot of stormbot
"""
import argparse
import shlex
import re

from abc import ABCMeta, abstractmethod
from sleekxmpp import ClientXMPP
import ssl

class Plugin(metaclass=ABCMeta):
    """Abstract plugin to be subclassed for each command of StormBot"""
    def __init__(self, bot, args=None):
        self._bot = bot

    def got_online(self, presence):
        pass

    @classmethod
    def argparser(cls, parser):
        """Build arg parser for stormbot (run from shell)"""
        pass

    @abstractmethod
    def cmdparser(self, parser):
        """Build command parser for stormbot (in chat)"""
        pass

    def message(self, nick, msg):
        pass

class Helper(Plugin):
    """Print help"""
    def cmdparser(self, parser):
        subparser = parser.add_parser('help', bot=self._bot)
        subparser.set_defaults(command=self.help)

    def help(self, msg, parser, *_):
        self._bot.write(parser.format_help())


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
    def __init__(self, args, password, plugins):
        super().__init__(args.jid, password)
        self.args = args
        self.room, _, self.nick = args.room.partition('/')
        self.nick = self.nick or "stormbot"
        self.plugins_cls = [Helper] + (plugins or [])
        self.plugins = []
        self.subscriptions = {}
        self.ssl_version = ssl.PROTOCOL_TLS

        self.add_event_handler("session_start", self.session_start)

        self.register_plugin('xep_0045') # MUC
        self.add_event_handler("groupchat_message", self.muc_message)
        self.add_event_handler("muc::{}::got_online".format(self.room), self.got_online)


    def session_start(self, _):
        """Start an xmpp session"""
        self.send_presence()
        self.plugin['xep_0045'].joinMUC(self.room, self.nick, wait=True)

    def got_online(self, presence):
        if presence['muc']['nick'] == self.nick:
            self.write("My dear masters,")
            # Init all plugins
            self.plugins = [plugin(self, self.args) for plugin in self.plugins_cls]

            # Init parser
            self.parser = CommandParser(description="stormbot executing your orders",
                                        prog=self.nick + ':', add_help=False,
                                        bot=self)
            subparsers = self.parser.add_subparsers()
            for plugin in self.plugins:
                plugin.cmdparser(subparsers)

            self.write("I'm now ready to execute your deepest desires.")
        else:
            for plugin in self.plugins:
                plugin.got_online(presence)

    def muc_message(self, msg):
        """Handle received message"""
        if msg['mucnick'] != self.nick:
            if msg['body'].startswith(self.nick + ':'):
                try:
                    self.command(msg)
                except CommandParserError as e:
                    self.write(e.message)
                    self.write(e.usage)
                except Exception as e:
                    import traceback
                    self.write("Are you trying to drive me insane?")
                    print(traceback.format_exc())
            elif msg['body'].startswith('all:'):
                try:
                    self.command(msg)
                except Exception:
                    pass
            else:
                match = re.search("^([^ :]+):", msg['body'])
                if match is None:
                    return

                nick = match.group(1)
                for plugin in self.subscriptions.get(nick, []):
                    try:
                        plugin.message(nick, msg)
                    except Exception as e:
                        self.write(e.message)

    def command(self, msg):
        """Handle a received command"""
        args = shlex.split(msg['body'])[1:]
        try:
            args = self.parser.parse_args(args)
            args.command(msg, self.parser, args)
        except CommandParserAbort:
            pass

    def write(self, string, *args, **kwargs):
        if len(args) > 0 or len(kwargs) > 0:
            string = string.format(*args, **kwargs)
        self.send_message(mto=self.room, mbody=string, mtype='groupchat')

    def subscribe(self, nick, plugin):
        if nick not in self.subscriptions:
            self.subscriptions[nick] = []
        self.subscriptions[nick].append(plugin)

class Fakebot:
    def write(sef, *args, **kwargs):
        print(*args, **kwargs)

def main(cls):
    argparser = argparse.ArgumentParser()
    cls.argparser(argparser)
    argparser.add_argument(dest="_", nargs='*')
    args = argparser.parse_args()
    plugin = cls(Fakebot(), args)

    parser = CommandParser()
    subparser = parser.add_subparsers()
    plugin.cmdparser(subparser)
    args = parser.parse_args(args._)
    plugin.run("todo", parser, args)
