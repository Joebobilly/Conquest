import unittest

from server_app.protocol import ProtocolError, parse_json_line


class ProtocolTests(unittest.TestCase):
    def test_valid_message(self):
        data = parse_json_line(b'{"type":"ping","request_id":"r1","protocol_version":1}\n')
        self.assertEqual(data["type"], "ping")

    def test_invalid_message(self):
        with self.assertRaises(ProtocolError):
            parse_json_line(b'not-json\n')

    def test_missing_type(self):
        with self.assertRaises(ProtocolError):
            parse_json_line(b'{"payload":{}}\n')


if __name__ == "__main__":
    unittest.main()
