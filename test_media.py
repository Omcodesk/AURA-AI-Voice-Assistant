"""
test_media.py — Unit tests for Media and Volume control logic.
Mocks pyautogui to verify key presses.
"""
import unittest
from unittest.mock import patch, MagicMock
from core.result_types import ParsedCommand
from actions.media_control import handle_media
from actions.system_control import handle_volume

class TestMediaControls(unittest.TestCase):
    @patch('actions.media_control.pyautogui')
    def test_media_actions(self, mock_pyauto):
        # 1. Test Play/Resume
        cmd = ParsedCommand(intent="media_control", action="play", source_text="play music")
        res = handle_media(cmd)
        self.assertTrue(res.success)
        mock_pyauto.press.assert_any_call("playpause")

        # 2. Test Next
        cmd = ParsedCommand(intent="media_control", action="next", source_text="next track")
        res = handle_media(cmd)
        self.assertTrue(res.success)
        mock_pyauto.press.assert_any_call("nexttrack")

    @patch('actions.system_control.pyautogui')
    def test_volume_actions(self, mock_pyauto):
        # 1. Test Volume Up with amount
        cmd = ParsedCommand(intent="volume", action="volume", source_text="volume up 20 percent", arguments={"amount": 20})
        res = handle_volume(cmd)
        self.assertTrue(res.success)
        # 20 percent / 2 = 10 steps
        mock_pyauto.press.assert_any_call('volumeup', presses=10)

        # 2. Test Mute
        cmd = ParsedCommand(intent="volume", action="volume", source_text="mute please")
        res = handle_volume(cmd)
        self.assertTrue(res.success)
        mock_pyauto.press.assert_any_call('volumemute')

if __name__ == "__main__":
    unittest.main()
