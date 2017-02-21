"""TTS for stormbot"""
import os
import subprocess
from .bot import Plugin


class Say(Plugin):
    def __init__(self, args):
        self.player = args.ttf_player
        self.voice = args.say_voice

    @classmethod
    def argparse(cls, parser):
        parser.add_argument("--ttf-player", type=str, default="espeak", help="Say TTF player (default: %(default)s)")
        parser.add_argument("--say-voice", type=str, default="fr-fr", help="Say voice (default: %(default)s)")

    def parser(self, parser):
        subparser = parser.add_parser('say')
        subparser.set_defaults(command=self.run)
        subparser.add_argument("--voice", type=str, default=self.voice, help="Say voice (default: %(default)s)")
        subparser.add_argument("text", type=str, help="Text to say")

    def run(self, bot, msg, parser, args):
        cmd = [self.player, '-v', self.voice, args.text]
        subprocess.Popen(cmd, stdin=None, stdout=None, stderr=None, close_fds=True)
