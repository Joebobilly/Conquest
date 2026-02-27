import tempfile
import unittest

from server_app.app import ConquestTCPServer
from server_app.config import ServerConfig
from server_app.db import connect


class DummyHandler:
    def __init__(self):
        self.user_id = None
        self.username = None


class ServerFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        config = ServerConfig(host='127.0.0.1', port=0, db_path=self.tmp.name, world_width=8, world_height=8, session_ttl_seconds=2)
        self.server = ConquestTCPServer(config)
        self.handler = DummyHandler()

    def tearDown(self):
        self.server.server_close()

    def dispatch(self, msg_type, payload=None):
        return self.server.dispatch(self.handler, {'type': msg_type, 'payload': payload or {}})

    def test_auth_register_login_resume_logout(self):
        registered = self.dispatch('auth.register', {'username': 'alice', 'password': 'supersecret'})
        self.assertEqual(registered['username'], 'alice')

        with self.assertRaises(ValueError):
            self.dispatch('auth.register', {'username': 'alice', 'password': 'anothersecret'})

        with self.assertRaises(ValueError):
            self.dispatch('auth.login', {'username': 'alice', 'password': 'wrongpass'})

        login = self.dispatch('auth.login', {'username': 'alice', 'password': 'supersecret'})
        token = login['token']
        self.assertIsNotNone(login['expires_at'])

        resumed = self.dispatch('auth.resume', {'token': token})
        self.assertEqual(resumed['username'], 'alice')

        logout = self.dispatch('auth.logout', {'token': token})
        self.assertEqual(logout, {'logged_out': True})

        with self.assertRaises(ValueError):
            self.dispatch('auth.resume', {'token': token})

    def test_expired_session_is_rejected(self):
        self.dispatch('auth.register', {'username': 'bob', 'password': 'supersecret'})
        login = self.dispatch('auth.login', {'username': 'bob', 'password': 'supersecret'})
        token = login['token']

        with connect(self.tmp.name) as conn:
            conn.execute('UPDATE sessions SET expires_at = 0 WHERE token = ?', (token,))
            conn.commit()

        with self.assertRaisesRegex(ValueError, 'expired'):
            self.dispatch('auth.resume', {'token': token})

    def test_world_state_requires_auth_and_claim_flow(self):
        self.dispatch('auth.register', {'username': 'charlie', 'password': 'supersecret'})
        self.dispatch('auth.login', {'username': 'charlie', 'password': 'supersecret'})

        with self.assertRaisesRegex(ValueError, 'Authentication required'):
            self.server.dispatch(DummyHandler(), {'type': 'world.state', 'payload': {}})

        state = self.dispatch('world.state')
        self.assertEqual(state['owned_tiles'], [{'x': 0, 'y': 0}])

        claimed = self.dispatch('action.claim', {'x': 1, 'y': 0})
        self.assertEqual(claimed['claimed'], {'x': 1, 'y': 0})

        with self.assertRaises(ValueError):
            self.dispatch('action.claim', {'x': 3, 'y': 3})

    def test_world_region_defaults_and_custom_bounds(self):
        self.dispatch('auth.register', {'username': 'daria', 'password': 'supersecret'})

        region = self.dispatch('world.region', {})
        self.assertEqual(len(region['tiles']), 64)

        small_region = self.dispatch('world.region', {'min_x': 0, 'min_y': 0, 'max_x': 1, 'max_y': 1})
        self.assertEqual(len(small_region['tiles']), 4)

    def test_payload_validation(self):
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.dispatch('auth.register', {'username': 'eve'})

        with self.assertRaisesRegex(ValueError, 'integer'):
            self.dispatch('world.region', {'min_x': 'bad'})

        self.dispatch('auth.register', {'username': 'eve', 'password': 'supersecret'})
        self.dispatch('auth.login', {'username': 'eve', 'password': 'supersecret'})

        with self.assertRaisesRegex(ValueError, '>= 1'):
            self.dispatch('action.claim', {'x': 1, 'y': 1, 'power_cost': 0})


if __name__ == '__main__':
    unittest.main()
