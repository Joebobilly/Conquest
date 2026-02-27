import os
import tempfile
import unittest

from server_app import db


class DBTests(unittest.TestCase):
    def test_initialize_with_filename_only_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                db.initialize('conquest.db', 4, 4)
                with db.connect('conquest.db') as conn:
                    row = conn.execute('SELECT width, height FROM world_meta WHERE id=1').fetchone()
                self.assertEqual((row['width'], row['height']), (4, 4))
            finally:
                os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
