import sqlite3
import json
from datetime import datetime, timezone
from functools import reduce

from . import all_subclasses
from .models import *
from .query import Query

from typing import get_origin

FOREIGN_KEY_SUFFIX = "_id"
DATATYPE_MAP = {
    str: "TEXT",
    int: "INTEGER",
    list: "TEXT",
    dict: "TEXT",
    float: "REAL",
    bool: "BOOLEAN",
    datetime: datetime.__name__,
    Model: "INTEGER",
}

class Storage:

    def __init__(self, file_path: str):

        # Adapter and converter for handling the datetime type
        def adapt_datetime_iso(val: datetime) -> str:
            return val.astimezone(timezone.utc).isoformat()

        def convert_datetime(val: bytes) -> datetime:
            return datetime.fromisoformat(val.decode()).astimezone()

        # Register adapter and converter for handling datetime datatype
        sqlite3.register_adapter(datetime, adapt_datetime_iso)
        sqlite3.register_converter(datetime.__name__, convert_datetime)

        # For using the converters for query parameters
        detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES

        def dict_factory(cursor, row):
            """Output keyed dict instead of list when querying"""
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.connection = sqlite3.connect(file_path, detect_types=detect_types)
        self.connection.row_factory = dict_factory

        # Turn foreign keys on
        self.connection.execute('PRAGMA foreign_keys = ON;')

        self._init_tables()
        self._init_orm()

    def _init_tables(self):
        """Initialize all the necessary tables"""
        # Loop over all the Model subclasses and initialize their tables if they're not template classes
        for model in all_subclasses(Model):
            if not model.template():
                self._generate_table_for_model(model)

    def _init_orm(self):
        """Add the objects hook to the model classes"""
        # Loop over all the Model subclasses and add orm functionalities
        for model in all_subclasses(Model):
            model.objects = Manager(model, self)

    def _generate_table_for_model(self, cls: type[Model]) -> None:
        query_parts = []
        foreign_keys = {}
        unique = []
        for name, datatype in cls.get_annotations().items():
            # Get rid of parameterized generics
            datatype = get_origin(datatype) or datatype

            # Check if the datatype is one of the types in DATATYPE_MAP or a subtype thereof
            if not reduce(lambda b1, b2: b1 or b2, map(lambda t: issubclass(datatype, t), DATATYPE_MAP.keys())):
                raise Exception(f"Datatype {datatype} for field {name} not supported!")

            # Check if the datatype is a model reference
            if issubclass(datatype, Model):
                sql_column_name = name + FOREIGN_KEY_SUFFIX
                sql_datatype = DATATYPE_MAP[Model]
                foreign_keys[sql_column_name] = datatype
            else:
                sql_column_name = name
                sql_datatype = DATATYPE_MAP[datatype]

            column_parts = []
            # Append name of the column
            column_parts.append(sql_column_name)

            # Append the datatype
            column_parts.append(sql_datatype)

            if name in cls.primary():
                column_parts.append(f"PRIMARY KEY")

            if name in cls.unique():
                unique.append(sql_column_name)

            # Append auto increment
            if name in cls.auto_increment():
                column_parts.append("AUTOINCREMENT")

            # Append column to the rest
            query_parts.append(" ".join(column_parts))

        # Add unique constraints in case there are any
        if cls.unique():
            query_parts.append(f"UNIQUE ({", ".join(cls.unique())})")

        # Add foreign keys
        for key, target_class in foreign_keys.items():
            query_parts.append(f"FOREIGN KEY ({key}) REFERENCES {target_class.__name__}({", ".join(target_class.primary())})")

        query = f"CREATE TABLE IF NOT EXISTS {cls.__name__} ({", ".join(query_parts)})"
        self.connection.execute(query)
        self.connection.commit()

    def _close(self):
        """Close the database connection."""
        self.connection.close()

    def delete(self, model: Model):
        """Delete a model from the database"""
        query = f"""DELETE FROM {model.__class__.__name__} WHERE id = {model.id}"""
        self.connection.execute(query)
        self.connection.commit()

    def load(self, model: type[Model], id: int) -> Model:
        if not id:
            return None
        query = f"""SELECT * FROM {model.__name__} WHERE id = {id}"""
        rows = self.direct_query(query)
        kwargs = rows.fetchone()
        if kwargs:
            return self._build(model, **kwargs)
        raise Exception(f"No entry with id: {id} in {model.__name__}")

    def _build(self, model: type[Model], **kwargs):
        model_kwargs = {}
        # Iterate over the model and format the values for insert query
        for key, datatype in model.get_annotations().items():
            # Get rid of parameterized generics
            datatype = get_origin(datatype) or datatype

            value = None
            if key in kwargs:
                value = kwargs[key]
            if key + FOREIGN_KEY_SUFFIX in kwargs:
                value = kwargs[key + FOREIGN_KEY_SUFFIX]

            # In case the value is a reference to another model, get the object from storage
            if issubclass(datatype, Model):
                model_kwargs[key] = self.load(datatype, value)
            elif issubclass(datatype, list):
                model_kwargs[key] = list(map(int, value.split(",")))
            elif issubclass(datatype, dict):
                model_kwargs[key] = json.loads(value)
            else:
                model_kwargs[key] = value

        return model(**model_kwargs)


    def create(self, type_: type[Model], **kwargs) -> Model:
        """Insert a model into the database"""
        if not kwargs:
            return None
        model = type_(**kwargs)
        model.save()
        return model


    def save(self, model: Model):
        """Save a model"""

        values = {}

        # Iterate over the model and format the values for insert query
        for key, datatype in model.__class__.get_annotations().items():
            # Get rid of parameterized generics
            datatype = get_origin(datatype) or datatype

            value = getattr(model, key)
            # In case the value is a reference to another model, just get its ID
            if issubclass(datatype, Model):
                if isinstance(value, Model):
                    value.save()
                    value = value.id
                values[key + FOREIGN_KEY_SUFFIX] = value
            elif issubclass(datatype, list):
                values[key] = ",".join(map(str, value))
            elif issubclass(datatype, dict):
                values[key] = json.dumps(value)
            else:
                values[key] = value

        query = f"""INSERT INTO {model.__class__.__name__} (
            {f", ".join(map(lambda key: key, values.keys()))})
            VALUES({f", ".join(map(lambda key: f":{key}", values.keys()))})
            ON CONFLICT(id) DO UPDATE SET
                {", ".join([f"{key}=excluded.{key}" for key in values.keys() if key != "id"])}
        """

        cursor = self.connection.execute(query, values)
        self.connection.commit()
        # If the model didn't have an ID before set it now
        if not model.id:
            model.id = cursor.lastrowid

    def direct_query(self, query: str):
        """Directly execute a query.

        Args:
            query (str): The query to execute.
            values (list): The values to insert.
        """
        cursor = self.connection.execute(query)
        self.connection.commit()
        return cursor

    def query(self, query: Query):
        sql_query = self.__build_sql_query(query=query)
        return self.direct_query(sql_query)

    def __build_sql_query(self, query: Query):
        pass


class Manager:
    """Manager that provides ORM functionality when attached to a Model"""
    model: type[Model]
    storage: Storage

    def __init__(self, model: type[Model], storage: Storage) -> None:
        self.model = model
        self.storage = storage

    def create(self, *args, **kwargs):
        return self.storage._build(self.model, *args, **kwargs)

    def save(self, model: Model):
        self.storage.save(model)

    # TODO: return a QuerySet or something similar here that does not excute the query right away
    # context: maybe the list is sliced, or indexed e.g. [1:4]
    def all(self) -> list[Model]:
        # Directly query the table if not a template.
        if not self.model.template():
            query = f"SELECT * FROM {self.model.__name__}"
        else:
            subclasses = all_subclasses(self.model)
            subqueries = []
            for subclass in subclasses:
                subqueries.append(f"SELECT {", ".join(self.model.get_annotations().keys())} FROM {subclass.__name__}")
            query = " UNION ".join(subqueries)

        rows = self.storage.direct_query(query)

        # Build the objects
        return [self.create(**row) for row in rows]

    def direct_query(self, query: str) -> list[Model]:
        return self.storage.direct_query(query).fetchall()

    def get_by_id(self, id: int):
        return self.storage.load(self.model, id)

    # TODO: See if we want to use a QuerySet here, just like the Django ORM
    def get(self, **kwargs) -> Model:
        """Get a specific object"""
        raise NotImplementedError()

    def filter(self, **kwargs) -> list[Model]:
        """Get a set of objects matching the filter"""
        raise NotImplementedError()
