import factory
from test_utils.async_factory import AsyncDjangoModelFactory


class UserFactory(AsyncDjangoModelFactory):
    class Meta:
        model = "accounts.User"
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "password")
