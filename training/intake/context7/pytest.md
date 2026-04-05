# pytest

pytest is a mature Python testing framework with powerful assertion introspection, fixture-based dependency injection, and 1300+ plugins. Supports Python 3.10+ and PyPy3.

## Fixtures and Parametrization

Parametrize at multiple levels: fixture params, @pytest.mark.parametrize, or pytest_generate_tests.

```python
import pytest

@pytest.fixture(params=[0, 1, pytest.param(2, marks=pytest.mark.skip)])
def data_set(request):
    return request.param

def test_data(data_set):
    pass
```

## conftest.py for Shared Fixtures

Share fixtures across test modules without explicit imports.

```python
# conftest.py
import pytest

@pytest.fixture
def db_connection():
    conn = create_connection()
    yield conn
    conn.close()

@pytest.fixture
def sample_user(db_connection):
    user = db_connection.create_user("test@example.com")
    yield user
    db_connection.delete_user(user.id)
```

## Markers for Test Categorization

Custom markers enable flexible test categorization and conditional execution.

```python
import pytest

@pytest.mark.slow
def test_large_dataset():
    pass

@pytest.mark.parametrize("input,expected", [
    ("hello", 5), ("world", 5), ("", 0),
])
def test_string_length(input, expected):
    assert len(input) == expected
```
