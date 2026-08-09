# Export Query Result

Use this command to execute a read-only SQL query and save its result as a CSV or JSON file.

## Required arguments

Ask for or extract these values from `$ARGUMENTS`:

- `database-id`: a saved database connection ID
- `format`: `csv` or `json`
- `query`: one read-only SQL statement
- `output`: optional output filename

## Workflow

1. Confirm that the requested SQL is a read-only query and that the format is `csv` or `json`.
2. Run `scripts/export-query.sh` with the supplied values.
3. Report the generated file path and format to the user.
4. If the command fails, show the backend error and do not create a success message.

Example:

```bash
./scripts/export-query.sh \
  --database-id "<database-id>" \
  --format csv \
  --query "select id, name from users order by id" \
  --output users.csv
```

The script calls `POST /api/v1/query/export`, so SQL validation, the default row limit, query history, and export formatting stay in one backend flow.
