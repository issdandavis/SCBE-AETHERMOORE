# PostgreSQL
> Source: Context7 MCP | Category: infra
> Fetched: 2026-04-04

### Execute a query for indexing demonstration

Source: https://www.postgresql.org/docs/18/indexes-intro.html

Represents a typical query that benefits from an index on the id column.

```sql
SELECT content FROM test1 WHERE id = _constant_;
```

---

### EXPLAIN with Index Scan

Source: https://www.postgresql.org/docs/18/sql-explain.html

Shows the execution plan when an index is utilized for a filtered query.

```sql
EXPLAIN SELECT * FROM foo WHERE i = 4;
```

---

### Chapter 11. Indexes

Source: https://www.postgresql.org/docs/18/indexes.html

Indexes are a common way to enhance database performance. An index allows the database server to find and retrieve specific rows much faster than it could do without an index. But indexes also add overhead to the database system as a whole, so they should be used sensibly.

---

### PostgreSQL 18 Documentation - Indexes

Source: https://www.postgresql.org/docs/18/indexes-intro.html

Indexes are database structures that improve the speed of data retrieval operations on a table. Without an index, the system must scan the entire table row by row to find matching entries, which is inefficient for large tables and frequent queries. An index allows the system to locate matching rows much more quickly, similar to how an index in a book helps readers find specific information without reading the entire book.

---

### Part II. The SQL Language > 11. Indexes

Source: https://www.postgresql.org/docs/18/sql.html

This chapter provides an introduction to indexes, covering different index types, multicolumn indexes, and how indexes are used with ORDER BY clauses.
