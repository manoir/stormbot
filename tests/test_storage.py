import io
import unittest

from stormbot.storage import Storage
from unittest.mock import patch, mock_open

class TestStorage(unittest.TestCase):
    @patch('stormbot.storage.Storage._load', lambda _: None)
    @patch("stormbot.storage.Storage._file", new_callable=io.StringIO, create=True)
    def test_store(self, cachefile):
        # Given
        storage = Storage("")

        # When
        storage["key"] = {}

        # Then
        self.assertEqual(cachefile.getvalue(), '{"key": {}}')

    @patch('stormbot.storage.Storage._load', lambda _: None)
    @patch("stormbot.storage.Storage._file", new_callable=io.StringIO, create=True)
    def test_store_multiple_times(self, cachefile):
        # Given
        storage = Storage("")

        # When
        storage["key"] = "a"
        storage["key"] = "b"

        # Then
        self.assertEqual(cachefile.getvalue(), '{"key": "b"}')

    @patch('stormbot.storage.Storage._load', lambda _: None)
    @patch("stormbot.storage.Storage._file", new_callable=io.StringIO, create=True)
    def test_store_subkey(self, cachefile):
        # Given
        storage = Storage("")
        storage["key"] = {}

        # When
        storage["key"]["subkey"] = "abc"

        # Then
        self.assertEqual(cachefile.getvalue(), '{"key": {"subkey": "abc"}}')

    @patch('builtins.open', mock_open(read_data='{"key": {}}'))
    @patch('os.path.isfile', lambda _: True)
    def test_load(self):
        # When
        storage = Storage("")

        # Then
        self.assertEqual(storage["key"], {})

    @patch('builtins.open', mock_open(read_data='{"key": {"subkey": "abc"}}'))
    @patch('os.path.isfile', lambda _: True)
    def test_load_subkey(self):
        # When
        storage = Storage("")

        # Then
        self.assertEqual(storage["key"]["subkey"], "abc")
