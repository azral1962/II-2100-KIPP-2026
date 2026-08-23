import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import load_env_file, resolve_project_path


class LoadEnvFileTest(unittest.TestCase):
    def test_loads_token_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "# Telegram configuration\nTELEGRAM_BOT_TOKEN=secret-token\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_env_file(env_path)

                self.assertEqual("secret-token", os.environ["TELEGRAM_BOT_TOKEN"])

    def test_does_not_override_process_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "TELEGRAM_BOT_TOKEN=file-token\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"TELEGRAM_BOT_TOKEN": "process-token"},
                clear=True,
            ):
                load_env_file(env_path)

                self.assertEqual("process-token", os.environ["TELEGRAM_BOT_TOKEN"])

    def test_resolves_relative_runtime_path_from_project(self) -> None:
        project = Path("C:/course")

        self.assertEqual(
            project / "data" / "antrian.csv",
            resolve_project_path(project, "data/antrian.csv"),
        )
        absolute = Path("C:/shared/antrian.csv")
        self.assertEqual(absolute, resolve_project_path(project, str(absolute)))


if __name__ == "__main__":
    unittest.main()
