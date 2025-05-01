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
