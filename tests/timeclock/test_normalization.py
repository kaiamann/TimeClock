from datetime import datetime
from timeclock import normalization
from timeclock.models import Model, Slot, Contract, User
from timeclock.utils import format_datetime


class TestGetNormalizerClass:

    def test_object_class(self):
        assert normalization.get_normalizer_class(object) == normalization.ObjectNormalizer

    def test_object_object(self):
        assert normalization.get_normalizer_class(object()) == normalization.ObjectNormalizer

    def test_slot_class(self):
        assert normalization.get_normalizer_class(Slot) == normalization.SlotNormalizer

    def test_slot_object(self):
        assert normalization.get_normalizer_class(Slot(start=datetime.now())) == normalization.SlotNormalizer

    def test_contract_class(self):
        assert normalization.get_normalizer_class(Contract) == normalization.SlotNormalizer

    def test_contract_object(self):
        contract = Contract(name="Test Contract", user=User(name="Test User"), start=datetime.now())
        assert normalization.get_normalizer_class(contract) == normalization.SlotNormalizer


class TestNormalizers:

    def test_empty_object(self):
        assert normalization.normalize(object()) == {}


    def test_models(self, example_models: list[Model]):
        for model in example_models:
            expected = dict(vars(model))

            # Edge case for Slot subclasses.
            if isinstance(model, Slot):
                expected["start"] = format_datetime(model.start)
                expected["end"] = format_datetime(model.end) if model.end else None

            # Normalize and verify
            normalized = normalization.normalize(model)
            assert normalized == expected

            # Denormalize and verify
            denormalized = normalization.denormalize(normalized, model.__class__)
            assert denormalized == model

    # def test_test(self, example_models: list[Model]):
    #     print(example_models)
