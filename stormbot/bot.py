"""
Main bot of stormbot
"""
import asyncio
import argparse
import shlex
import re
import logging
import pkg_resources

from abc import ABCMeta, abstractmethod
from slixmpp import ClientXMPP, Iq
from slixmpp.exceptions import IqError
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin
from slixmpp.jid import JID
from slixmpp.plugins.base import BasePlugin
from slixmpp.xmlstream.handler.callback import Callback
from slixmpp.xmlstream.matcher.xpath import MatchXPath
from distutils.version import LooseVersion
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


class PeerPlugins(ElementBase):
    namespace = "https://github.com/manoir/stormbot:1#plugins"
    name = "query"
    plugin_attrib = "plugins"


class PeerCommand(ElementBase):
    namespace = "https://github.com/manoir/stormbot:1#command"
    name = "query"
    plugin_attrib = "command"


class StormbotPeering(BasePlugin):
    name = "stormbot_peering"
    namespace = "https://github.com/manoir/stormbot:1"
    description = "Stormbot peer communication"
    dependencies = {'xep_0030'}

    def plugin_init(self):
        self._plugins = []
        self.xmpp.register_handler(Callback('Peer plugins',
                                           MatchXPath('{%s}iq/{%s}query' % (self.xmpp.default_ns, PeerPlugins.namespace)),
                                           self._handle_plugins))
        register_stanza_plugin(Iq, PeerPlugins)

        self.xmpp.register_handler(Callback('Peer command',
                                           MatchXPath('{%s}iq/{%s}query' % (self.xmpp.default_ns, PeerCommand.namespace)),
                                           self._handle_command))
        register_stanza_plugin(Iq, PeerCommand)

    def plugin_end(self):
        self.xmpp.plugin['xep_0030'].del_feature(feature=self.namespace)

    def session_bind(self, jid):
        self.xmpp.plugin['xep_0030'].add_feature(self.namespace)
        for plugin in self._plugins:
            self.xmpp.plugin['xep_0030'].add_item(node=self.namespace,
                                                  jid=plugin)

    def add_plugin(self, name, version):
        self._plugins.append(f"{name}#{version}")

    def _handle_plugins(self, iq):
        logging.debug("Received peer plugins iq")
        if iq['type'] == 'get':
            self.xmpp.event('peer_plugins_get', iq)
        elif iq['type'] == 'result':
            self.xmpp.event('peer_plugins_result', iq)
        else:
            logging.error(f"Got unknown iq type for plugins {iq['type']}")

    def _handle_command(self, iq):
        logging.debug("Received peer command iq")
        if iq['type'] == 'set':
            self.xmpp.event('peer_command', iq)
        else:
            logging.error(f"Got unknown iq type for command {iq['type']}")


class Peer:
    def __init__(self, room, nick):
        self._room = room
        self._nick = nick
        self._plugins = {}

    @property
    def jid(self):
        return f"{self._room}/{self._nick}"

    def add_plugin(self, name, version):
        self._plugins[name] = {'name': name, 'version': version}

    def supports(self, name, version):
        return name in self._plugins \
                and LooseVersion(self._plugins[name]['version']) >= LooseVersion(version)


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
        self._peers = {}

        self.add_event_handler("session_start", self.session_start)

        self.register_plugin('xep_0030') # Discovery
        self.register_plugin('xep_0045') # MUC
        self.register_plugin('StormbotPeering', module=self.__class__.__module__)
        self.add_event_handler("peer_plugins_get", self._plugins_get)
        self.add_event_handler("peer_plugins_result", self._plugins_result)
        self.add_event_handler("peer_command", self._peer_recv_command)
        self.add_event_handler("command_set", self._plugins_result)
        self.add_event_handler("groupchat_message", self._muc_message)
        self.add_event_handler("muc::{}::got_online".format(self.room), self.got_online)

        # Init all plugins
        self.plugins = [plugin(self, self.args) for plugin in self.plugins_cls]

        # Init parser
        self.cmd_parser = CommandParser(description="stormbot executing your orders",
                                    prog=self.nick + ':', add_help=False,
                                    bot=self)
        subparsers = self.cmd_parser.add_subparsers()
        for plugin in self.plugins:
            plugin.cmdparser(subparsers)

            try:
                distribution = pkg_resources.get_distribution(plugin.__class__.__module__)
            except pkg_resources.DistributionNotFound:
                continue

            self.plugin['StormbotPeering'].add_plugin(distribution.project_name, distribution.version)


    def session_start(self, _):
        """Start an xmpp session"""
        self.send_presence()
        self.plugin['xep_0045'].join_muc(self.room, self.nick, wait=True)

    async def got_online(self, presence):
        if presence['muc']['nick'] != self.nick:
            for plugin in self.plugins:
                plugin.got_online(presence)

            await self._handle_peer(presence)

    def _muc_message(self, msg):
        """Handle received muc message"""
        if msg['mucnick'] != self.nick:
            if msg['body'].startswith(self.nick + ':'):
                try:
                    self._command(msg)
                except CommandParserError as e:
                    self.write(e.message)
                    self.write(e.usage)
                except Exception as e:
                    import traceback
                    self.write("Are you trying to drive me insane?")
                    print(traceback.format_exc())
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

    def _command(self, msg, peer=False):
        """Handle a received command"""
        args = shlex.split(msg['body'])[1:]
        try:
            args = self.cmd_parser.parse_args(args)
            args.command(msg, self.cmd_parser, args, peer)
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

    async def _handle_peer(self, presence):
        nick = presence['muc']['nick']
        is_peer = await self._is_peer(nick)
        if is_peer:
            await self._peer_connect(presence['muc']['room'], presence['muc']['nick'])

    async def _is_peer(self, nick):
        if len(nick) == 0:
            return False

        info = await self.plugin['xep_0030'].get_info(jid=f"{self.room}/{nick}")
        return StormbotPeering.namespace in info['disco_info']['features']

    def _peer_send(self, peer, msg):
        self.send_message(mto=peer.jid, mbody=msg, mtype="chat")

    def _plugins_get(self, iq):
        query = iq['plugins']
        plugins = ET.Element('plugins')

        for plugin in self.plugins:
            try:
                distribution = pkg_resources.get_distribution(plugin.__class__.__module__)
            except pkg_resources.DistributionNotFound:
                continue

            entry_point = f"{plugin.__class__.__module__}:{plugin.__class__.__name__}"
            plugin = ET.Element('plugin')
            plugin.set('name', distribution.project_name)
            plugin.set('version', distribution.version)
            plugin.set('entry_point', entry_point)
            plugins.append(plugin)

        query.xml.append(plugins)
        iq.reply().setPayload(query.xml)
        iq.send()

    def _plugins_result(self, iq):
        jid = JID(iq['from'])
        if jid.bare != self.room or jid.resource not in self._peers:
            logging.error("Received plugin list from unknown peer")
            return

        peer = self._peers[jid.resource]
        plugins = iq['plugins'].xml.find("{%s}plugins" % PeerPlugins.namespace)
        for plugin in plugins:
            peer.add_plugin(plugin.get('name'), plugin.get('version'))

    def peer_send_command(self, plugin, peer, msg):
        distribution = pkg_resources.get_distribution(plugin.__class__.__module__)

        iq = self.make_iq_set(ito=peer.jid)
        query = ET.Element("{%s}query" % PeerCommand.namespace)
        plugin_et = ET.Element("plugin")
        plugin_et.set('name', distribution.project_name)
        plugin_et.set('version', distribution.version)
        query.append(plugin_et)

        command_et = ET.Element("command")
        command_et.set('from', msg['mucnick'])
        command_et.text = msg['body']
        query.append(command_et)
        iq.xml.append(query)
        try:
            iq.send()
        except IqError as e:
            logging.info("Peer couldn't execute command: %s", e)


    def _peer_recv_command(self, iq):
        jid = JID(iq['from'])
        if jid.bare != self.room or jid.resource not in self._peers:
            logging.error("Received command from unknown peer")
            return

        peer = self._peers[jid.resource]
        plugin_et = iq['command'].xml.find("{%s}plugin" % PeerCommand.namespace)
        command = iq['command'].xml.find("{%s}command" % PeerCommand.namespace)

        for plugin in self.plugins:
            try:
                distribution = pkg_resources.get_distribution(plugin.__class__.__module__)
            except pkg_resources.DistributionNotFound:
                continue

            if distribution.project_name == plugin_et.get('name') \
               and distribution.version == plugin_et.get('version'):
                msg = {'mucnick': command.get('from'), 'body': command.text}
                try:
                    self._command(msg, True)
                except Exception as e:
                    iq.error().send()
                iq.reply().send()
                return

        logging.error("Received command for unsupported plugin")

    async def _peer_connect(self, room, nick):
        logging.info(f"Connecting to peer {self.room}/{nick}")

        if nick in self._peers:
            del self._peers[nick]

        try:
            items = await self.plugin['xep_0030'].get_items(jid=f"{self.room}/{nick}",
                                                              node=StormbotPeering.namespace)
            self._peers[nick] = Peer(self.room, nick)
            for plugin in items['disco_items']['items']:
                name, version = plugin[0].split('#')
                self._peers[nick].add_plugin(name, version)

        except IqError as e:
            logging.error(f"Couldn't connect to peer {room}/{nick}: {e.iq['error']['condition']}")

    def get_peers(self, plugin=None):
        if plugin is None:
            return self._peers.values()
        else:
            distribution = pkg_resources.get_distribution(plugin.__class__.__module__)
            return filter(lambda p: p.supports(distribution.project_name, distribution.version), self._peers.values())

class Fakebot:
    def write(sef, *args, **kwargs):
        print(*args, **kwargs)

def main(cls):
    argparser = argparse.ArgumentParser()
    cls.argparser(argparser)
    argparser.add_argument(dest="_", nargs='*')
    args = argparser.parse_args()
    plugin = cls(Fakebot(), args)

    cmd_parser = CommandParser()
    subparser = cmd_parser.add_subparsers()
    plugin.cmdparser(subparser)
    args = cmd_parser.parse_args(args._)
    plugin.run("todo", cmd_parser, args)
