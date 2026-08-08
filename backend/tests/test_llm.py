import unittest

from fastapi import HTTPException

from db_query_backend import llm


class LlmHelperTests(unittest.TestCase):
    def test_build_schema_context_includes_columns_and_constraints(self) -> None:
        context = llm.build_schema_context(
            [
                {
                    "id": "users-table",
                    "schema_name": "public",
                    "table_name": "users",
                    "table_type": "BASE TABLE",
                }
            ],
            [
                {
                    "table_id": "users-table",
                    "column_name": "id",
                    "data_type": "integer",
                    "is_primary_key": 1,
                    "is_nullable": 0,
                }
            ],
        )

        self.assertIn("TABLE public.users", context)
        self.assertIn("id: integer [PRIMARY KEY, NOT NULL]", context)

    def test_extracts_fenced_sql(self) -> None:
        self.assertEqual(llm._extract_query("```sql\nSELECT 1;\n```"), "SELECT 1")

    def test_extracts_json_sql(self) -> None:
        self.assertEqual(llm._extract_query('{"sql":"SELECT 1;"}'), "SELECT 1")

    def test_requires_api_key(self) -> None:
        original_key = llm.settings.openai_api_key
        try:
            object.__setattr__(llm.settings, "openai_api_key", "")
            with self.assertRaises(HTTPException) as context:
                llm.generate_query("show users", "TABLE public.users")
            self.assertEqual(context.exception.status_code, 503)
        finally:
            object.__setattr__(llm.settings, "openai_api_key", original_key)


if __name__ == "__main__":
    unittest.main()
