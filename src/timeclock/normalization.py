from abc import ABC, abstractmethod
from . import all_subclasses
from .models import Slot, Model
from .utils import format_datetime, datetime_from_string
from typing import get_type_hints

class Normalizer(ABC):

    target_class: type
    normalizer_map = {}
    denormalizer_map = {}

    @classmethod
    @abstractmethod
    def normalize(cls: type, obj: object) -> dict:
        """Normalize an object.

        Args:
            obj (object): The object to normalize

        Returns:
            dict: The object in normalized form.
        """


    @classmethod
    @abstractmethod
    def denormalize(cls:type, data: dict, target_class: type = None) -> object:
        """Denormalize some data into an object.

        Args:
            data (dict): The data to denormalize

        Returns:
            object_class: The denormalized object.
        """

class ObjectNormalizer(Normalizer):

    target_class = object

    @classmethod
    def normalize(cls: type, obj: object) -> dict:
        try:
            data = vars(obj)
            for key, value in data.items():
                if value and key in cls.normalizer_map:
                    data[key] = cls.normalizer_map[key](value)
            return data
        except TypeError:
            return {}

    @classmethod
    def denormalize(cls:type, data: dict, target_class: type = None) -> object:
        target_class = target_class or cls.target_class
        type_hints = get_type_hints(target_class)
        # Iterate though the data and cast to the correct type.
        for key, value in data.items():
            if value and key in type_hints:
                print("key", key, "value", value, "typehint" , type_hints[key])
                # If an explicit denormalization function has been specified use it.
                if key in cls.denormalizer_map:
                    data[key] = cls.denormalizer_map[key](value)
                # If it's a model just copy over the values
                elif isinstance(value, Model):
                    data[key] = value
                # Otherwise just cast to the annotated type.
                else:
                    data[key] = type_hints[key](value)

        print(data)
        return target_class(**data)


class SlotNormalizer(ObjectNormalizer):
    target_class = Slot
    normalizer_map = {
        'start': format_datetime,
        'end': format_datetime,
    }
    denormalizer_map = {
        'start': datetime_from_string,
        'end': datetime_from_string,
    }


def normalize(obj: object) -> dict:
    """Normalize an object.

    Args:
        obj (object): The object to be normalized

    Returns:
        dict: The normalized object
    """
    return get_normalizer_class(obj).normalize(obj)

def denormalize(data: dict, cls: type) -> dict:
    """Denormalize data into an object.

    Args:
        data (dict): The data to be denormalized
        cls: (type): The desired class.

    Returns:
        object: The denormalized object
    """
    normalizer_class = get_normalizer_class(cls)
    print(normalizer_class, cls)
    return normalizer_class.denormalize(data, cls)

def get_normalizer_class(object_or_class: type|object) -> type[Normalizer]:
    """Get the most specific normalizer class for the given object or class.

    Args:
        object_class (type): An object or class

    Returns:
        type:  The most specific normalizer class
    """
    target_class = object_or_class
    # Check if the parameter is not a type, if it isn't get its class.
    if not isinstance(object_or_class, type):
        target_class = object_or_class.__class__

    # Check all subclasses of Normalizer and choose the fitting one.
    for subclass in all_subclasses(Normalizer):
        if subclass.target_class == target_class:
            return subclass

    # In case none fit check the base classes.
    for base in target_class.__bases__:
        parent_normalizer = get_normalizer_class(base)
        # In case the base class has a more specific normalizer than the ObjectNormalizer return it.
        if parent_normalizer != ObjectNormalizer:
            return parent_normalizer
    return ObjectNormalizer
