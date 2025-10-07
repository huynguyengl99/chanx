import json
from pathlib import Path

from django.urls import reverse
from rest_framework.test import APITestCase

results_dir = Path(__file__).parent / "test_results"


class AsyncAPISchemaTestCase(APITestCase):
    def test_json_schema(self) -> None:
        response = self.client.get(reverse("asyncapi_schema"))
        data = response.json()
        with open(results_dir / "asyncapi_schema_res.json", "w") as f:
            json.dump(data, f, indent=2)

        with open(results_dir / "asyncapi_schema.json") as f:
            expected_data = json.load(f)

        assert data == expected_data

    def test_yaml_schema(self) -> None:
        response = self.client.get(reverse("asyncapi_schema") + "?format=yaml")
        data = response.text
        with open(results_dir / "asyncapi_schema_res.yaml", "w") as f:
            f.write(data)

        with open(results_dir / "asyncapi_schema.yaml") as f:
            expected_data = f.read()

        assert data == expected_data
