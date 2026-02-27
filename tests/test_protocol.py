import unittest

from server_app.protocol import parse_json_line


class ProtocolTests(unittest.TestCase):
    def test_valid_message(self):
        data = parse_json_line(b'{"type":"ping"}\n')
        self.assertEqual(data["type"], "ping")

    def test_invalid_message(self):
        with self.assertRaises(ValueError):
            parse_json_line(b'not-json\n')


if __name__ == "__main__":
    unittest.main()
