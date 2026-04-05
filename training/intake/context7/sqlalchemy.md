# SQLAlchemy
> Source: Context7 MCP | Category: code
> Fetched: 2026-04-04

### ORM Querying Guide

Source: https://docs.sqlalchemy.org/en/20/orm/contextual.html

The ORM Querying Guide explains how to retrieve data from the database using Python objects and expressions. Instead of writing raw SQL, developers can construct queries using the ORM's query API, which is more Pythonic and less error-prone. This guide covers various querying techniques, including filtering, sorting, joining, and selecting specific columns, all while maintaining an object-oriented approach.

---

### Define ORM Models and Initialize Database

Source: https://docs.sqlalchemy.org/en/20/orm/queryguide/_plain_setup.html

Defines the DeclarativeBase models for a user-address-order-item schema and initializes an in-memory SQLite engine.

```python
from typing import List, Optional
from sqlalchemy import Column, create_engine, ForeignKey, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    fullname: Mapped[Optional[str]]
    addresses: Mapped[List["Address"]] = relationship(back_populates="user")
    orders: Mapped[List["Order"]] = relationship()

class Address(Base):
    __tablename__ = "address"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    email_address: Mapped[str]
    user: Mapped[User] = relationship(back_populates="addresses")

order_items_table = Table(
    "order_items",
    Base.metadata,
    Column("order_id", ForeignKey("user_order.id"), primary_key=True),
    Column("item_id", ForeignKey("item.id"), primary_key=True),
)

class Order(Base):
    __tablename__ = "user_order"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    items: Mapped[List["Item"]] = relationship(secondary=order_items_table)

class Item(Base):
    __tablename__ = "item"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]

engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)
session = Session(engine)
session.add_all([User(name="spongebob", fullname="Spongebob Squarepants")])
session.commit()
```

---

### Basic Querying with select()

Source: https://docs.sqlalchemy.org/en/20/orm/session_basics.html

Shows how to perform basic ORM queries using the `select()` construct.

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

with Session(engine) as session:
    # query for User objects
    statement = select(User).filter_by(name="ed")
    user_obj = session.scalars(statement).all()

    # query for individual columns
    statement = select(User.name, User.fullname)
    rows = session.execute(statement).all()
```

---

### Constructing and Executing a SELECT Statement

Source: https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html

Demonstrates how to build a SELECT statement for ORM mapped classes using the `select()` function and execute it with a `Session`.

```python
from sqlalchemy import select

stmt = select(User).where(User.name == "spongebob")

result = session.execute(stmt)

for user_obj in result.scalars():
    print(f"{user_obj.name} {user_obj.fullname}")
```

---

### Writing SELECT statements for ORM Mapped Classes

Source: https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html

This section covers writing SELECT statements for ORM Mapped Classes, including:
- Selecting ORM entities and attributes
- Performing joins and utilizing relationship WHERE operators
- Selecting individual entities, multiple entities simultaneously, and individual attributes
- Grouping selected attributes with bundles
- Using ORM aliases
- Obtaining ORM results from textual statements
- Selecting entities from subqueries and UNIONs
- Various join techniques (relationship joins, chaining, aliased targets, subquery joins)
- Relationship WHERE operators such as EXISTS forms (`has()`/`any()`) and instance comparison operators
