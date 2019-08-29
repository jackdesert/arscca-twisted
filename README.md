Arscca-Websocket
================

This repository provides an autobahn/twisted server with a websocket.

Setup
-----

Python3.6 or greater is required, because this project uses F-strings.

    cd /path/to/project
    python3 -m venv env
    env/bin/pip install autobahn twisted treq pyopenssl service_identity
    env/bin/pip freeze > requirements.txt


Explanation of Packages
-----------------------

    autobahn:       wrapper for twisted
    twisted:        asynchronous I/O, including websockets
    treq:           asynchronous GET and POST requests that work with the twisted reactor
    pyopenssl:      required by treq if you want to access sites over SSL
    service_identy: pyopenssl gives strange errors if you don't include this



Production Setup
----------------

You will probably want to set the slack url in config/environment.txt

    cd /path/to/project
    cd config
    cp environment.txt-EXAMPLE environment.txt
    vi environment.txt


### Install Packages from requirements.txt

    env/bin/pip install -r requirements.txt




Run
---

    env/bin/python run.py



Development Files
-----------------

The files index.html and index-log-delta.html were used in the development process
and are no longer needed. You may want to keep them around in case something breaks.
They work somewhat like a test-in-a-box.


Backlog
-------

  -
