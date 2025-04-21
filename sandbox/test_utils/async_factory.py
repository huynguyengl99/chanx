from asgiref.sync import sync_to_async
from factory.django import DjangoModelFactory


class AsyncDjangoModelFactory(DjangoModelFactory):
    @classmethod
    async def acreate(cls, **kwargs):
        return await sync_to_async(cls.create)(**kwargs)
