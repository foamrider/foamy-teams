import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('teams_launch', Path(__file__).resolve().parents[1] / 'launch.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LaunchTest(unittest.TestCase):
    def test_invalid_input(self):
        for value in [None, [], '', [3], [''], ['app', '\0']]:
            self.assertFalse(module.launch(value))

    def test_missing_executable(self):
        self.assertFalse(module.launch(['/nonexistent/foamy-teams-test']))

    def test_literal_arguments_and_detached_session(self):
        with patch.object(module.subprocess, 'Popen') as spawn:
            self.assertTrue(module.launch(['client', '$(touch /tmp/never)', 'two words']))
            self.assertEqual(spawn.call_args.args[0], ['client', '$(touch /tmp/never)', 'two words'])
            self.assertTrue(spawn.call_args.kwargs['start_new_session'])
            self.assertNotIn('shell', spawn.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
