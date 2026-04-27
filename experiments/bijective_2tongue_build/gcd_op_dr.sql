-- Recursive CTE GCD: schema lane. SQLite-compatible.
WITH RECURSIVE g(a, b) AS (
  SELECT 462, 1071
  UNION ALL
  SELECT b, a % b FROM g WHERE b != 0
)
SELECT a FROM g WHERE b = 0;
