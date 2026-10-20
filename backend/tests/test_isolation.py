import unittest
from unittest.mock import patch

import database


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.params = None

    def execute(self, sql, params):
        self.params = params
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return {"total": len(self.rows)}


class _Connection:
    def __init__(self, rows):
        self.cursor = _Cursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params):
        return self.cursor.execute(sql, params)


class UserIsolationTests(unittest.TestCase):
    def test_history_queries_always_scope_to_requested_user(self):
        rows = [{"id": 1, "input_data": {"marker": "user-a"}, "result_data": {}}]
        connection = _Connection(rows)
        with patch.object(database, "connection", return_value=connection):
            user_a_rows = database.list_predictions("user_a")
            user_a_count = database.count_predictions("user_a")

        self.assertEqual(user_a_rows, rows)
        self.assertEqual(user_a_count, 1)
        self.assertIn("user_a", connection.cursor.params)
        self.assertNotIn("user_b", connection.cursor.params)

    def test_filter_builder_cannot_return_unscoped_query(self):
        where, values = database._history_filters("user_b", query="marker")
        self.assertTrue(where.startswith("user_id = %s"))
        self.assertEqual(values[:1], ["user_b"])
        self.assertIn("input_data::text ILIKE", where)

    def test_batch_persistence_uses_cursor_executemany(self):
        class BatchCursor:
            def __init__(self):
                self.rows = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def executemany(self, sql, rows):
                self.rows = list(rows)

        class BatchConnection:
            def __init__(self):
                self.cursor_instance = BatchCursor()
                self.committed = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def cursor(self):
                return self.cursor_instance

            def commit(self):
                self.committed = True

        connection = BatchConnection()
        records = [({"marker": "batch"}, {"Risk_Level": "Low Risk"})]
        with patch.object(database, "connection", return_value=connection):
            saved = database.save_predictions("user_a", records, "csv")

        self.assertEqual(saved, 1)
        self.assertEqual(len(connection.cursor_instance.rows), 1)
        self.assertTrue(connection.committed)


if __name__ == "__main__":
    unittest.main()
