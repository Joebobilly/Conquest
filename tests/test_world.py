import tempfile
import unittest

from server_app import db
from server_app.protocol import ProtocolError
from server_app.world import WorldService


class WorldServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.initialize(self.tmp.name, 8, 8)

    def _world(self, conn):
        return WorldService(conn, default_power=100, max_power=100, power_regen_per_tick=1, tick_seconds=2.0)

    def test_spawn_and_claim(self):
        with db.connect(self.tmp.name) as conn:
            world = self._world(conn)
            world.create_user_resources(1)
            sx, sy = world.spawn_for_user_if_needed(1)
            self.assertEqual((sx, sy), (0, 0))
            claim = world.claim_tile(1, 1, 0)
            self.assertEqual(claim["claimed"], {"x": 1, "y": 0})
            self.assertEqual(claim["resources"]["power"], 95)

    def test_claim_requires_adjacency(self):
        with db.connect(self.tmp.name) as conn:
            world = self._world(conn)
            world.create_user_resources(2)
            world.spawn_for_user_if_needed(2)
            with self.assertRaises(ProtocolError):
                world.claim_tile(2, 3, 3)

    def test_attack_and_build_and_patches(self):
        with db.connect(self.tmp.name) as conn:
            world = self._world(conn)
            world.create_user_resources(1)
            world.create_user_resources(2)
            world.spawn_for_user_if_needed(1)
            world.spawn_for_user_if_needed(2)
            conn.execute("UPDATE land_tiles SET owner_user_id = 1 WHERE x=1 AND y=0")
            conn.execute("UPDATE land_tiles SET owner_user_id = 2 WHERE x=2 AND y=0")
            conn.commit()
            built = world.build_on_tile(1, 1, 0, "camp")
            self.assertEqual(built["built"]["building_type"], "camp")
            captured = world.attack_tile(2, 1, 0)
            self.assertEqual(captured["captured"], {"x": 1, "y": 0})
            patches = world.patches_since(0)
            self.assertGreaterEqual(patches["to_version"], 4)
            self.assertTrue(any(e["event_type"] == "tile.attack_capture" for e in patches["events"]))


if __name__ == "__main__":
    unittest.main()
