from stormbot.storage import Storage
from unittest.mock import patch, mock_open
from nose.tools import *
import io

@patch('stormbot.storage.Storage._load', lambda _: None)
@patch("stormbot.storage.Storage._file", new_callable=io.StringIO, create=True)
def test_store(cachefile):
    # Given
    storage = Storage("")

    # When
    storage["key"] = {}

    # Then
    eq_(cachefile.getvalue(), '{"key": {}}')

@patch('stormbot.storage.Storage._load', lambda _: None)
@patch("stormbot.storage.Storage._file", new_callable=io.StringIO, create=True)
def test_store_multiple_times(cachefile):
    # Given
    storage = Storage("")

    # When
    storage["key"] = "a"
    storage["key"] = "b"

    # Then
    eq_(cachefile.getvalue(), '{"key": "b"}')

@patch('stormbot.storage.Storage._load', lambda _: None)
@patch("stormbot.storage.Storage._file", new_callable=io.StringIO, create=True)
def test_store_subkey(cachefile):
    # Given
    storage = Storage("")
    storage["key"] = {}

    # When
    storage["key"]["subkey"] = "abc"

    # Then
    eq_(cachefile.getvalue(), '{"key": {"subkey": "abc"}}')

@patch('builtins.open', mock_open(read_data='{"key": {}}'))
@patch('os.path.isfile', lambda _: True)
def test_load():
    # When
    storage = Storage("")

    # Then
    eq_(storage["key"], {})

@patch('builtins.open', mock_open(read_data='{"key": {"subkey": "abc"}}'))
@patch('os.path.isfile', lambda _: True)
def test_load_subkey():
    # When
    storage = Storage("")

    # Then
    eq_(storage["key"]["subkey"], "abc")
