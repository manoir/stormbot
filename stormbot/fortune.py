"""Fortune for stormbot"""
import sys
import random
import argparse
from pkg_resources import resource_string

from .bot import Plugin

class Fortune(Plugin):
    def __init__(self, bot, args):
        self._bot = bot
        self._sentences = args.fortune_dict.decode().splitlines()

    @classmethod
    def argparser(cls, parser):
        default_dict = resource_string(__name__, 'data/kaamelott.dic')
        parser.add_argument("--fortune-dict", type=argparse.FileType('r'), default=default_dict,
                            help="Dictionnary to use for fortune (default: kaamelott)")

    def cmdparser(self, parser):
        subparser = parser.add_parser('fortune', bot=self._bot)
        subparser.set_defaults(command=self.run)
        if 'stormbot.say' in sys.modules:
            subparser.add_argument("--say", dest="say", action="store_true", help="Say the fortune quote")

    def random(self):
        return random.choice(self._sentences)

    def run(self, msg, parser, args):
        quote = self.random()
        if args.say:
            say_args = ["say", quote]
            say_args = parser.parse_args(say_args)
            say_args.command(msg, parser, say_args)
        else:
            self._bot.write(quote)
