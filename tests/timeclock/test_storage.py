from timeclock.models import Model
from timeclock.storage import Storage, Manager


class TestStorage():

    def test_insert(self, storage: Storage, example_models: list[Model]):
        models = []
        for model in example_models:
            orm = model.__class__.objects
            assert orm.all() == models
            print(model)
            storage.create(model)
            models.append(model)
            print(orm.all())
            assert orm.all() == models



    def test_insert_delete(self, storage: Storage, example_models: list[Model]):
        for model in example_models:
            orm = model.__class__.objects
            # print(model, "dict", model.__dict__)
            assert orm.all() == []
            storage.create(model)
            print(orm.all())
            assert all([o1.id == o2.id for o1, o2 in zip(orm.all(), [model])])
            storage.delete(model)

