## v2.1.1 (2025-12-05)

### Fix

- correct codegen type for literal and any

## v2.1.0 (2025-11-28)

### Feat

- client generator

### Fix

- update docs for client generation
- improve code gen for dict and add some hooks, error handling for base client
- add tests for the client generation feature
- use netloc instead of hostname for fastapi autodoc

### Refactor

- restructure optional dependencies into focused extras

## v2.0.2 (2025-11-15)

### Fix

- suppress mypy override warning for EmailUserField.to_representation
- use aexception for channel event ValidationError to capture full traceback

## v2.0.1 (2025-10-13)

### Fix

- **docs**: minor fix for tutorial docs
- **docs**: add AsyncAPI mapping explanations and improve navigation
- **docs**: add comprehensive FastAPI Chanx WebSocket tutorial
- **packages**: correct package dependencies
- **docs**: add comprehensive Django WebSocket tutorial and framework comparison

## v2.0.0 (2025-10-12)

### BREAKING CHANGE

- Import paths changed from chanx.ext.channels to chanx.channels and chanx.ext.fast_channels to chanx.fast_channels

### Feat

- restructure package and adopt mixin pattern for better static type checking

## v1.1.3 (2025-10-11)

### Fix

- **core**: support list/tuple output types in handlers

## v1.1.2 (2025-10-11)

### Fix

- **core**: add missing init file to core

## v1.1.1 (2025-10-11)

### Fix

- **asyncapi**: preserve schema keys as PascalCase class names in camelCase mode

## v1.1.0 (2025-10-10)

### Feat

- **asyncapi**: add camelCase naming convention support

## v1.0.4 (2025-10-10)

### Fix

- properly handle nested references in $defs schemas for message registry

## v1.0.3 (2025-10-10)

### Fix

- properly handle $defs references in AsyncAPI schemas

## v1.0.2 (2025-10-09)

### Fix

- improve DjangoAuthenticator flexibility and type safety

## v1.0.1 (2025-10-09)

### Fix

- improve queryset handling in DjangoAuthenticator

## v1.0.0 (2025-10-08)

### BREAKING CHANGE

- Major rewrite introducing decorator-based WebSocket handlers and automatic AsyncAPI documentation generation

### Feat

- reimplement chanx with decorator approach and auto-generate asyncapi docs

### Fix

- install all extras for readthedocs
- update documentation and improve type safety in message registry

## v0.13.3 (2025-07-15)

### Fix

- **packages**: loosen package dependencies versions

## v0.13.2 (2025-07-12)

### Fix

- **testing**: ignore CancelledError for WebsocketTestCase tearDown

## v0.13.1 (2025-07-12)

### Fix

- **deps**: replace channels-stubs with types-channels

## v0.13.0 (2025-06-07)

### Feat

- **messages**: remove outgoing group message system and simplify generic types

## v0.12.0 (2025-06-07)

### Feat

- **testing**: add receive_until_action method for flexible message collection

## v0.11.2 (2025-06-06)

### Fix

- **websocket**: use json mode for message serialization

## v0.11.1 (2025-06-02)

### Fix

- **websocket**: add AbstractBaseUser support for custom user models

## v0.11.0 (2025-05-28)

### Feat

- **event**: replace dynamic method dispatch with receive_event for channel events

## v0.10.0 (2025-05-27)

### Feat

- **event**: add typed channel event system with static type checking
- **generic**: add generic type parameters and simplify message architecture

## v0.9.0 (2025-05-15)

### Feat

- **playground**: camelize websocket endpoint responses and update affected variables

## v0.8.0 (2025-05-15)

### Feat

- **path_param**: support for django path converter param within angle bracket

## v0.7.1 (2025-05-15)

### Fix

- **docs**: update testing docs to remind user to set SEND_COMPLETION to true for properly testing

## v0.7.0 (2025-05-15)

### Feat

- **routing**: migrate path and re_path from urls module to routing module for consistency and update docs

## v0.6.1 (2025-05-12)

### Fix

- **py.typed**: add py.typed to let static type checker know that chanx has fulfilled type hint

## v0.6.0 (2025-05-11)

### Feat

- **python310**: add support for python version 310
- **websocket**: add kind to broadcast_message to handle both pydantic message and json case

### Fix

- **pyright**: remove pyright section in pyproject toml and use python 310 for pyright python target version
- **sandbox**: update sandbox api schema auth and group chat serializer fields
- **docs**: only create docs if the commit message is the bump version message

## v0.5.0 (2025-05-09)

### Feat

- **pyright,urls**: add support for (based)pyright and urls path,repath utils

### Fix

- **basedpyright,yml,ci**: fix yml indent, ci branches to run and basedpyright venv path in tox
- **tox**: install camel-case for all env in tox

## v0.4.0 (2025-05-02)

### Feat

- **types**: add and update type annotations for the entire project, and install channels stubs as well

### Fix

- **dev**: migrate django-environ to environs for better typing support, and update user type hint
- **refactor**: remove redundant code or comments

## v0.3.0 (2025-04-22)

### Feat

- **camelize**: add ability to auto convert incoming and outgoing message between snake and camelcase for fe compatibility

### Fix

- **jwt**: migrate jwt packages from extra dependencies to jwt group

## v0.2.3 (2025-04-22)

### Fix

- **interrogate**: move interrogate badge to docs _static folder to serve on readthedocs

## v0.2.2 (2025-04-22)

### Refactor

- **readthedocs**: force readthedocs to install the extras package

## v0.2.1 (2025-04-22)

### Fix

- **commitizen**: add update uv.lock before bump and use shortcuts option

### Refactor

- **commitizen**: remove unused section

## v0.2.0 (2025-04-22)

## v0.1.0 (2025-04-21)

### Feat

- **authenticator**: refactor and enhance authenticator of chanx websocket consumer
- **playground**: improve playground websocket path params handling
- **chanx**: enhance authentication using drf object permission, and add path param for playground
- **utils,websocket**: create reuseable websocket utils and add transform function for playground to transform websocket route info
- **utils**: migrate and separate utils function under utils package with separate meaningful file module
- **auth,testing**: improve auth message, and add test helper as well as the first test case
- **chanx**: add routing utility and update base incoming message
- **chanx**: write workable version for chanx and create sandbox app
- **init-project**: start the chanx project

### Fix

- **group,refactor**: add some more group helper, add some more tests for group cases and some extra testing utils
- **testing**: update testing get websocket header function
- **python**: target python 3.11+ and remove support for python 3.10
- **pydantic**: force user to use pydantic v2
- **redis**: add redis to github test workflow
- **test.yml**: add postgres service to github test workflow
- **test,coverage**: update coveragerc and test command

### Refactor

- **websocket.js**: refactor big js file to multiple sub files to easier maintain and enhance
- **websocket.html**: separate websocket html to different files (html, css, js) for easier maintain and update
- **sandbox-chat**: migrate sandbox chat app to assistants
- **websocket**: authenticated request get from response without fallback to original request
