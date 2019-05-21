import io

from functools import wraps
from unittest.mock import patch, MagicMock

def bot(argv):
    argv = [argv[0]] + argv
    def decorator(f):
        stdout = io.StringIO()
        wrapped = patch('stormbot.bot.Fakebot.write', lambda _, *args, **kwargs: print(*args, **kwargs, file=stdout))(f)
        wrapped = patch('sys.exit', lambda _: None)(f)
        wrapped = patch('sys.argv', argv)(wrapped)

        def wrapping(*args, **kwargs):
            args += (stdout,)
            wrapped(*args, **kwargs)

        return wrapping

    return decorator

def storage(values):
    def decorator(f):
        wrapper = patch('stormbot.storage.Storage._load', lambda _: None)(f)
        wrapper = patch('stormbot.storage.Storage.__getitem__', lambda _, key: values.__getitem__(key))(wrapper)
        wrapper = patch('stormbot.storage.Storage.__contains__', lambda _, key: values.__contains__(key))(wrapper)

        return wrapper
    return decorator
