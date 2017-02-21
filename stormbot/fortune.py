"""Fortune for stormbot"""
import random
import argparse
from pkg_resources import resource_string

from .bot import Plugin

class Fortune(Plugin):
    def __init__(self, args):
        self._sentences = args.fortune_dict.decode().splitlines()

    @classmethod
    def argparse(cls, parser):
        default_dict = resource_string(__name__, 'data/kaamelott.dic')
        parser.add_argument("--fortune-dict", type=argparse.FileType('r'), default=default_dict,
                            help="Dictionnary to use for fortune (default: kaamelott)")

    def parser(self, parser):
        subparser = parser.add_parser('fortune')
        subparser.set_defaults(command=self.run)

    def random(self):
        return random.choice(self._sentences)

    def run(self, bot, msg, *_):
        bot.send_message(mto=msg['from'].bare, mbody=self.random(), mtype='groupchat')
