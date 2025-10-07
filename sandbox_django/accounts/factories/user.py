import factory
from test_utils.factory import BaseModelFactory

from accounts.models import User


class UserFactory(BaseModelFactory[User]):
    email = factory.Faker("email")  # type:ignore[attr-defined,no-untyped-call]
    password = "password"
    is_active = True
    is_superuser = False
    is_staff = False
