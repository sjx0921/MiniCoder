import os
import tempfile
import unittest
from pathlib import Path

from config import load_dotenv


class DotEnvTests(unittest.TestCase):
    def test_loads_values_without_overwriting_existing_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TEST_MINICODER_VALUE=from_file\nTEST_MINICODER_EXISTING=from_file\n", encoding="utf-8")
            old_value = os.environ.get("TEST_MINICODER_EXISTING")
            try:
                os.environ["TEST_MINICODER_EXISTING"] = "from_shell"
                load_dotenv(path)
                self.assertEqual(os.environ["TEST_MINICODER_VALUE"], "from_file")
                self.assertEqual(os.environ["TEST_MINICODER_EXISTING"], "from_shell")
            finally:
                os.environ.pop("TEST_MINICODER_VALUE", None)
                if old_value is None:
                    os.environ.pop("TEST_MINICODER_EXISTING", None)
                else:
                    os.environ["TEST_MINICODER_EXISTING"] = old_value


if __name__ == "__main__":
    unittest.main()
