FTS_SEARCH_SQL = """
SELECT
  bm25(sections_fts, 8.0, 4.0, 2.0, 1.0) AS score,
  source_id,
  rel_path,
  title,
  snippet(sections_fts, 3, '', '', ' … ', 24) AS snippet
FROM sections_fts
WHERE sections_fts MATCH :query
ORDER BY score
LIMIT :limit
"""
