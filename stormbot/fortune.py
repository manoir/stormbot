"""Fortune for stormbot"""
import random
import argparse
from pkg_resources import resource_string

from .bot import Plugin

class Fortune(Plugin):
    def __init__(self, args):
        self._sentences = args.fortune_dict.decode().splitlines()

    @classmethod
    def argparser(cls, parser):
        default_dict = resource_string(__name__, 'data/kaamelott.dic')
        parser.add_argument("--fortune-dict", type=argparse.FileType('r'), default=default_dict,
                            help="Dictionnary to use for fortune (default: kaamelott)")

    def cmdparser(self, parser, bot):
        subparser = parser.add_parser('fortune', bot=bot)
        subparser.set_defaults(command=self.run)
        subparser.add_argument("--say", dest="say", action="store_true", help="Say the fortune quote")

    def random(self):
        return random.choice(self._sentences)

    def run(self, bot, msg, parser, args):
        quote = self.random()
        if args.say:
            say_args = ["say" , quote]
            say_args = parser.parse_args(say_args)
            say_args.command(bot, msg, parser, say_args)
        else:
            bot.write(quote)
