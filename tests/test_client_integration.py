import tempfile
import threading
import unittest

from client_app import ConquestClient
from client_app.protocol import ProtocolError, decode_response, encode_request
from server_app.app import ConquestTCPServer
from server_app.config import ServerConfig


class ClientProtocolTests(unittest.TestCase):
    def test_encode_request(self):
        packet = encode_request("ping")
        self.assertEqual(packet, b'{"type":"ping"}\n')

    def test_decode_response_error(self):
        with self.assertRaises(ProtocolError):
            decode_response(b'{"type":"error","error":"nope"}\n')


class ClientIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()

        config = ServerConfig(
            host="127.0.0.1",
            port=0,
            db_path=self.tmp.name,
            world_width=8,
            world_height=8,
            session_ttl_seconds=120,
        )
        self.server = ConquestTCPServer(config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_client_end_to_end(self):
        client = ConquestClient(self.host, self.port)
        hello = client.connect()
        self.assertEqual(hello["type"], "hello")

        client.register("alice", "supersecret")
        login = client.login("alice", "supersecret")
        token = login["token"]

        resumed = client.resume(token)
        self.assertEqual(resumed["username"], "alice")

        state = client.world_state()
        self.assertEqual(state["owned_tiles"], [{"x": 0, "y": 0}])

        claim = client.claim(1, 0)
        self.assertEqual(claim["claimed"], {"x": 1, "y": 0})

        meta = client.world_meta()
        self.assertEqual(meta, {"width": 8, "height": 8})

        region = client.world_region(min_x=0, min_y=0, max_x=1, max_y=1)
        self.assertEqual(len(region["tiles"]), 4)

        ping = client.ping()
        self.assertTrue(ping["pong"])

        logout = client.logout(token)
        self.assertEqual(logout, {"logged_out": True})

        with self.assertRaises(ProtocolError):
            client.resume(token)

        client.close()


if __name__ == "__main__":
    unittest.main()
