import importlib.util
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).with_name("tac_run_maestro_selftest.py")
SPEC = importlib.util.spec_from_file_location("tac_run_maestro_selftest", SCRIPT_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)

BUG_SCRIPT_PATH = Path(__file__).with_name("tac_create_bug_from_maestro_result.py")
BUG_SPEC = importlib.util.spec_from_file_location("tac_create_bug_from_maestro_result", BUG_SCRIPT_PATH)
bug_generator = importlib.util.module_from_spec(BUG_SPEC)
assert BUG_SPEC.loader is not None
BUG_SPEC.loader.exec_module(bug_generator)


class MaestroCommandTest(TestCase):
    def test_default_flow_path_uses_persistent_baseline(self):
        expected = runner.os.path.join(
            "persistent-assets",
            "automated-testing",
            "_baseline",
            "flows",
        )
        self.assertEqual(runner.DEFAULT_FLOW_PATH, expected)
        self.assertEqual(bug_generator.DEFAULT_FLOW_PATH, expected)

    def test_windows_prefers_maestro_bat(self):
        def fake_which(command):
            return "C:\\Users\\TINNOVE\\.maestro\\maestro\\bin\\maestro.bat" if command == "maestro.bat" else None

        with patch.object(runner.platform, "system", return_value="Windows"), \
             patch.object(runner.shutil, "which", side_effect=fake_which), \
             patch.dict(runner.os.environ, {}, clear=True):
            self.assertEqual(
                runner.maestro_cmd(),
                "C:\\Users\\TINNOVE\\.maestro\\maestro\\bin\\maestro.bat",
            )

    def test_env_overrides_path_lookup(self):
        with patch.dict(runner.os.environ, {"MAESTRO_BIN": "D:\\tools\\maestro.cmd"}):
            self.assertEqual(runner.maestro_cmd(), "D:\\tools\\maestro.cmd")

    def test_explicit_path_overrides_env(self):
        with patch.dict(runner.os.environ, {"MAESTRO_BIN": "D:\\tools\\maestro.cmd"}):
            self.assertEqual(runner.maestro_cmd("C:\\custom\\maestro.bat"), "C:\\custom\\maestro.bat")

    def test_do_run_maestro_uses_resolved_command(self):
        calls = []

        class Result:
            returncode = 0

        def fake_run_cmd(args, **_kwargs):
            calls.append(args)
            return Result()

        with patch.object(runner, "maestro_cmd", return_value="C:\\maestro\\bin\\maestro.bat"), \
             patch.object(runner, "run_cmd", side_effect=fake_run_cmd):
            exit_code = runner.do_run_maestro(
                "device-1",
                "flow.yaml",
                "report.xml",
                "results",
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0][0], "C:\\maestro\\bin\\maestro.bat")


if __name__ == "__main__":
    main()
