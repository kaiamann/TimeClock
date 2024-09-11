from enum import Enum
import types
import typing
from .models import Model

class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class OrderType(Enum):
    ASCENDING = "ASC"
    DESCENDING = "DESC"

class Attribute:
    alias: str
    name: str
    model: type

    def __init__(self, model: Model, name: str, alias: str = None) -> None:
        self.model = model
        self.name = name
        self.alias = alias

class Order:
    attribute: Attribute
    order_type: OrderType

    def __init__(self, attribute: Attribute, order_type: OrderType) -> None:
        self.attribute = attribute
        self.order_type = order_type

class Literal:
    value: str|int|list

class Condition:
    func: typing.Callable|str
    operands: list[Attribute|Literal]

    def __init__(self, func: typing.Callable|str, *operands: list[Attribute|Literal]) -> None:
        self.operands = operands
        self.func = func

class Query:
    """Rudimentary implementation of query abstraction."""
    query_type: QueryType
    return_attributes: list[Attribute]
    conditions: list[Condition]
    order_by: list[Order]

    def __init__(self, query_type: QueryType, return_attributes: list[Attribute]) -> None:
        self.query_type = query_type
        self.return_attributes = return_attributes
        self.conditions = []
        self.order_by = []

    def condition(self, func: typing.Callable|str, *operands: list[Attribute|Literal]) -> "Query":
        self.conditions.append(Condition(func, *operands))
        return self

    def order_by(self, attribute: Attribute, order_type: OrderType = OrderType.ASCENDING) -> "Query":
        self.order_by.append(Order(attribute=attribute, order_type=order_type))
        return self


class QueryBuilder:
    def build(query: Query) -> str:
        raise NotImplementedError()

class SQLBuilder(QueryBuilder):
    """Rudimentary implementation of an SQL query builder"""

    def build(self, query: Query) -> str:
        query_parts = [query.query_type.value, "FROM"]

        # Get all the necessary tables
        models = set(attribute.model.__name__ for attribute in query.return_attributes)
        query_parts.extend(models)

        if query.conditions:
            query_parts.append("WHERE")

            for condition in query.conditions:
                query_parts.append(self.build_condition(condition))
        return " ".join(query_parts)

    def build_condition(self, condition: Condition) -> str:
        condition_parts = []
        match str(condition.func).upper():
            case "BETWEEN":
                condition_parts.append(condition.operands[0].alias or condition.operands[0].name)
                condition_parts.append("BETWEEN")
                condition_parts.extend(str(op) for op in condition.operands[1:])
            case _:
                pass
        return " ".join(condition_parts)
