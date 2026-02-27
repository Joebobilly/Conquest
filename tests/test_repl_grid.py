import unittest

from client_app.repl import render_world_grid


class ReplGridRenderTests(unittest.TestCase):
    def test_render_world_grid_uses_ascii_tokens(self):
        meta = {"width": 4, "height": 2}
        tiles = [
            {"x": 0, "y": 0, "terrain": "water", "owner_user_id": None},
            {"x": 1, "y": 0, "terrain": "land", "owner_user_id": None},
            {"x": 2, "y": 0, "terrain": "land", "owner_user_id": 1},
            {"x": 3, "y": 0, "terrain": "land", "owner_user_id": 2},
            {"x": 0, "y": 1, "terrain": "land", "owner_user_id": None},
            {"x": 1, "y": 1, "terrain": "water", "owner_user_id": None},
            {"x": 2, "y": 1, "terrain": "land", "owner_user_id": 2},
            {"x": 3, "y": 1, "terrain": "water", "owner_user_id": None},
        ]

        rendered = render_world_grid(meta, tiles)

        self.assertEqual(rendered, "-012\n0-2-")


if __name__ == "__main__":
    unittest.main()
