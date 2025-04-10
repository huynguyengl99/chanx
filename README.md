# chanx

The missing toolkit for Django Channels — auth, logging, consumers, and more.

## Installation

The module can be installed from [PyPI](https://pypi.org/project/chanx/):

```bash
pip install chanx
```

## Document
Please visit [chanx doc](https://chanx.readthedocs.io/) for
documentation.

## Introduction

### Why Choose chanx?
Due to the lack of some features of the great package `django-channels`, this one will
fill the missing gap for users

### Features
- Playground for websocket, with automatically discover websocket routes.
- JWTAuthentication + Permission for websocket connection, with the help of `dj-rest-auth` + `restframework-simplejwt`.
- Logging for websocket json message, in order to help you trace the in and out message flow.
### Dependencies
