import io
import asyncio

from .bot import StormBot
from functools import wraps
from unittest.mock import patch, MagicMock, Mock
from collections.abc import MutableMapping

def bot(plugin):
    bot = None
    args = MagicMock()
    args.jid = 'stormbot@example.org'
    args.room = 'room@conference.example.org/stormbot'
    bot = StormBot(args, '', [plugin])
    bot.send_message = Mock()

    def run_command(command):
        msg = {}
        msg['body'] = command
        return asyncio.get_event_loop().run_until_complete(bot._command(msg))

    bot.command = run_command

    return bot

class Storage(MutableMapping):
    def __init__(self):
        self._storage = {}

    def __setitem__(self, key, value):
        return self._storage.__setitem__(key, value)

    def __delitem__(self, key):
        return self._storage.__delitem__(key)

    def __getitem__(self, key):
        return self._storage.__getitem__(key)

    def __iter__(self):
        return self._storage.__iter__(self)

    def __len__(self):
        return self.__storage.__len__(self)

    def __call__(self, path):
        return self
