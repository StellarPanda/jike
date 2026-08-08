import unittest

from fastapi import HTTPException

from db_query_backend.query_engine import validate_readonly_query


class QueryEngineTests(unittest.TestCase):
    def test_adds_default_limit_to_select(self) -> None:
        result = validate_readonly_query("select * from users")

        self.assertTrue(result.applied_limit)
        self.assertEqual(result.limit_value, 1000)
        self.assertIn("LIMIT 1000", result.normalized_query)

    def test_rejects_write_queries(self) -> None:
        with self.assertRaises(HTTPException) as context:
            validate_readonly_query("delete from users")

        self.assertEqual(context.exception.status_code, 400)

    def test_rejects_multiple_statements(self) -> None:
        with self.assertRaises(HTTPException) as context:
            validate_readonly_query("select 1; select 2")

        self.assertIn("single SQL statement", str(context.exception.detail))

    def test_rejects_large_limit(self) -> None:
        with self.assertRaises(HTTPException) as context:
            validate_readonly_query("select * from users limit 5001")

        self.assertIn("5000", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
