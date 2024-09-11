import json

from timeclock.serialization import JSONSerializer, CSVSerializer

class TestJSONSerializer:

    def test_serialize(self):
        serializer = JSONSerializer()

        test_data = {
            "example_int": 1,
            "example_float": 2.4,
            "example_string": "string",
            "example_int_list": [1,2,3,4],
            "example_str_list": ["1","2","3","4"],
            "example_json_child": {
                "example_int": 1,
            },
        }
        assert serializer.serialize(test_data) == json.dumps(test_data)

    def test_deserialize(self):
        serializer = JSONSerializer()
        test_data = {
            "example_int": 1,
            "example_float": 2.4,
            "example_string": "string",
            "example_int_list": [1,2,3,4],
            "example_str_list": ["1","2","3","4"],
            "example_json_child": {
                "example_int": 1,
            },
        }

        assert serializer.deserialize(json.dumps(test_data)) == test_data


class TestCSVSerializer:

    def test_serialize(self):
        test_data = {
            "example_int": 1,
            "example_float": 2.4,
            "example_string": "string",
        }
        serializer = CSVSerializer(test_data.keys())

        expected = "example_int,example_float,example_string\n1,2.4,string\n"
        assert serializer.serialize(test_data) == expected

    def test_deserialize(self):
        serialized = "example_int,example_float,example_string\n1,2.4,string\n"

        # the datatypes cannot be inferred by the CSV structure, hence everything is a string.
        expected = {
            "example_int": "1",
            "example_float": "2.4",
            "example_string": "string",
        }
        serializer = CSVSerializer(list(expected.keys()))

        assert serializer.deserialize(serialized) == [expected]


