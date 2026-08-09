import csv
import io
import json
import unittest

from db_query_backend.exporter import build_export_file
from db_query_backend.schemas import QueryExecutionResponse, QueryResultColumn


def sample_result() -> QueryExecutionResponse:
    return QueryExecutionResponse(
        database_id="demo",
        executed_query="SELECT id, name FROM users LIMIT 1000",
        row_count=2,
        columns=[
            QueryResultColumn(key="id", title="id"),
            QueryResultColumn(key="name", title="name"),
        ],
        rows=[{"id": 1, "name": "Ava Chen"}, {"id": 2, "name": "李明"}],
    )


class ExporterTests(unittest.TestCase):
    def test_builds_csv_with_header_and_rows(self) -> None:
        content, media_type, filename = build_export_file(sample_result(), "csv")
        rows = list(csv.reader(io.StringIO(content.decode("utf-8"))))

        self.assertEqual(media_type, "text/csv; charset=utf-8")
        self.assertTrue(filename.endswith(".csv"))
        self.assertEqual(rows, [["id", "name"], ["1", "Ava Chen"], ["2", "李明"]])

    def test_builds_json_with_query_and_rows(self) -> None:
        content, media_type, filename = build_export_file(sample_result(), "json")
        payload = json.loads(content.decode("utf-8"))

        self.assertEqual(media_type, "application/json; charset=utf-8")
        self.assertTrue(filename.endswith(".json"))
        self.assertEqual(payload["rowCount"], 2)
        self.assertEqual(payload["rows"][1]["name"], "李明")


if __name__ == "__main__":
    unittest.main()
