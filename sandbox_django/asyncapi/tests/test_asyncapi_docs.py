from django.urls import reverse
from rest_framework.test import APITestCase


class AsyncAPIDocsTestCase(APITestCase):
    def test_docs(self) -> None:
        response = self.client.get(reverse("asyncapi_docs"))
        html_content = response.content.decode("utf-8")
        assert "CHANX AsyncAPI Documentation" in html_content
        assert "AsyncApiStandalone.render" in html_content
