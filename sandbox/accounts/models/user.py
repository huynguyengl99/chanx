from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast

from django.contrib import auth
from django.contrib.auth.models import AbstractUser, BaseUserManager, Permission
from django.db import models
from django.db.models import Model, QuerySet
from django.db.models.expressions import Combinable

from chat.models import GroupChat

if TYPE_CHECKING:
    from django.contrib.auth.backends import ModelBackend

_T = TypeVar("_T", bound=AbstractUser)


class UserManager(BaseUserManager[_T]):
    use_in_migrations = True

    def _create_user_object(self, email: str, password: str, **extra_fields: Any) -> _T:
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        return user

    def _create_user(self, email: str, password: str, **extra_fields: Any) -> _T:
        """
        Create and save a user with the given username, email, and password.
        """
        user = self._create_user_object(email, password, **extra_fields)
        user.save(using=self._db)
        return user

    async def _acreate_user(self, email: str, password: str, **extra_fields: Any) -> _T:
        """See _create_user()"""
        user = self._create_user_object(email, password, **extra_fields)
        await user.asave(using=self._db)
        return user

    def create_user(self, email: str, password: str, **extra_fields: Any) -> _T:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    create_user.alters_data = True  # type: ignore

    async def acreate_user(self, email: str, password: str, **extra_fields: Any) -> _T:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return await self._acreate_user(email, password, **extra_fields)

    acreate_user.alters_data = True  # type: ignore

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> _T:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    create_superuser.alters_data = True  # type: ignore

    async def acreate_superuser(
        self, email: str, password: str, **extra_fields: Any
    ) -> _T:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return await self._acreate_user(email, password, **extra_fields)

    acreate_superuser.alters_data = True  # type: ignore

    def with_perm(
        self,
        perm: str | Permission,
        is_active: bool = True,
        include_superusers: bool = True,
        backend: str | None = None,
        obj: Model | None = None,
    ) -> QuerySet[_T]:
        if backend is None:
            backends = auth.get_backends()
            if len(backends) == 1:
                load_backend = backends[0]
            else:
                raise ValueError(
                    "You have multiple authentication backends configured and "
                    "therefore must provide the `backend` argument."
                )
        elif not isinstance(
            backend, str
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"backend must be a dotted import path string (got {backend})."
            )
        else:
            load_backend = auth.load_backend(backend)

        load_backend = cast(ModelBackend, load_backend)
        if hasattr(load_backend, "with_perm"):
            return cast(
                QuerySet[_T],
                load_backend.with_perm(
                    perm,
                    is_active=is_active,
                    include_superusers=include_superusers,
                    obj=obj,
                ),
            )
        return self.none()


class User(AbstractUser):
    email = models.EmailField[str | Combinable, str](
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    objects: ClassVar[UserManager[User]] = UserManager["User"]()  # type: ignore[assignment]

    username = None  # type: ignore[assignment]
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    chat_groups: QuerySet[GroupChat]

    def __str__(self) -> str:
        return str(self.email)
