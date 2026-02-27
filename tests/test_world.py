import tempfile
import unittest

from server_app import db
from server_app.world import WorldService


class WorldServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.initialize(self.tmp.name, 8, 8)

    def tearDown(self):
        pass

    def test_spawn_and_claim(self):
        with db.connect(self.tmp.name) as conn:
            world = WorldService(conn, default_power=100, max_power=100, power_regen_per_tick=1, tick_seconds=2.0)
            world.create_user_resources(1)
            sx, sy = world.spawn_for_user_if_needed(1)
            self.assertEqual((sx, sy), (0, 0))

            claim = world.claim_tile(1, 1, 0)
            self.assertEqual(claim["claimed"], {"x": 1, "y": 0})
            self.assertEqual(claim["resources"]["power"], 95)

    def test_claim_requires_adjacency(self):
        with db.connect(self.tmp.name) as conn:
            world = WorldService(conn, default_power=100, max_power=100, power_regen_per_tick=1, tick_seconds=2.0)
            world.create_user_resources(2)
            world.spawn_for_user_if_needed(2)
            with self.assertRaises(ValueError):
                world.claim_tile(2, 3, 3)


if __name__ == "__main__":
    unittest.main()
