"""Saving must still work when the history file is mounted into a Docker container.

Docker cannot replace a single mounted file, so os.replace fails there with
"Device or resource busy". These tests simulate that failure; no Docker needed.
"""

import errno
import json
import os
import tempfile
import unittest
from unittest import mock

from data_manager import JsonDataManager


class TestSaveWhenTheFileCannotBeReplaced(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name
        self.path = os.path.join(self.folder, "recipes_history.json")
        self.manager = JsonDataManager(file_path=self.path)

    @staticmethod
    def busy(*args, **kwargs):
        raise OSError(errno.EBUSY, "Device or resource busy")

    def saved_json(self):
        with open(self.path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_save_succeeds_and_keeps_old_records_when_replace_is_refused(self):
        self.assertTrue(self.manager.save_record({"record_id": 1}))

        with mock.patch("os.replace", side_effect=self.busy):
            self.assertTrue(self.manager.save_record({"record_id": 2}))

        self.assertEqual(self.saved_json(), [{"record_id": 1}, {"record_id": 2}])
        self.assertEqual(self.manager.load_records(), [{"record_id": 1}, {"record_id": 2}])

    def test_no_temporary_files_are_left_behind(self):
        with mock.patch("os.replace", side_effect=self.busy):
            self.manager.save_record({"record_id": 1})

        self.assertEqual(os.listdir(self.folder), ["recipes_history.json"])

    def test_normal_saves_do_not_use_the_fallback(self):
        with mock.patch.object(JsonDataManager, "_write_in_place") as fallback:
            self.assertTrue(self.manager.save_record({"record_id": 1}))

        fallback.assert_not_called()
        self.assertEqual(self.saved_json(), [{"record_id": 1}])

    def test_save_reports_failure_when_the_fallback_also_fails(self):
        self.manager.save_record({"record_id": 1})

        with mock.patch("os.replace", side_effect=self.busy), \
                mock.patch.object(JsonDataManager, "_write_in_place", side_effect=OSError("read-only")):
            self.assertFalse(self.manager.save_record({"record_id": 2}))

        self.assertEqual(self.saved_json(), [{"record_id": 1}])

    def test_unserialisable_record_still_cannot_damage_the_history(self):
        self.manager.save_record({"record_id": 1})

        with mock.patch("os.replace", side_effect=self.busy):
            self.assertFalse(self.manager.save_record({"record_id": float("nan")}))

        self.assertEqual(self.saved_json(), [{"record_id": 1}])


if __name__ == "__main__":
    unittest.main(verbosity=2)