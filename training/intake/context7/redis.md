# Redis
> Source: Context7 MCP | Category: infra
> Fetched: 2026-04-04

### Cache Repository with Spring Data Redis

Source: https://github.com/redis/docs/blob/main/content/integrate/spring-framework-cache/_index.md

This example demonstrates how to configure a repository to use Spring Data Redis for caching. It utilizes the @CacheConfig annotation to specify the cache name and the @Cacheable annotation on a method to enable caching of its results. This reduces the execution of costly methods by storing and reusing their results.

```java
@CacheConfig("books")
public class BookRepositoryImpl implements BookRepository {

    @Cacheable
    public Book findBook(ISBN isbn) {...}
}
```

---

### Store Filtered Cache Entries with Tags in Python

Source: https://github.com/redis/docs/blob/main/content/develop/ai/redisvl/user_guide/llmcache.md

This Python code snippet demonstrates how to initialize a `SemanticCache` with a 'user_id' tag and store cache entries associated with specific user IDs. It shows how to ensure that data is segregated by user.

```python
from redisvl.semantic_cache import SemanticCache

private_cache = SemanticCache(
    name="private_cache",
    filterable_fields=[{"name": "user_id", "type": "tag"}]
)

private_cache.store(
    prompt="What is the phone number linked to my account?",
    response="The number on file is 123-555-0000",
    filters={"user_id": "abc"},
)

private_cache.store(
    prompt="What's the phone number linked in my account?",
    response="The number on file is 123-555-1111",
    filters={"user_id": "def"},
)
```

---

### Store Data in Semantic Cache (Python)

Source: https://github.com/redis/docs/blob/main/content/develop/ai/redisvl/user_guide/llmcache.md

This Python code snippet shows how to store a question, its corresponding response, and associated metadata into the Redis semantic cache. The metadata is stored as a Python dictionary.

```python
llmcache.store(
    prompt=question,
    response="Paris",
    metadata={"city": "Paris", "country": "france"}
)
```

---

### What is Redis?

Source: https://github.com/redis/docs/blob/main/AGENT.md

Redis is an open-source, in-memory data structure store used as a database, cache, message broker, and streaming engine. It supports various data structures such as strings, hashes, lists, sets, sorted sets, bitmaps, hyperloglogs, geospatial indexes, and streams.

---

### Redis Data Integration

Source: https://github.com/redis/docs/blob/main/content/integrate/redis-data-integration/_index.md

When a relational database struggles to scale with a growing user base, RDI offers a solution by using a fast database like Redis to cache data from read queries. Since read queries are far more frequent than writes, this caching significantly boosts performance and allows applications to scale without major architectural changes. RDI maintains this Redis cache by tracking changes in the primary database through a Change Data Capture (CDC) mechanism. It also allows for data transformation from relational tables into efficient data structures tailored to application needs, all configured without requiring any coding.
