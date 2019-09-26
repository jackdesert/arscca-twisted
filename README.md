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


### Systemd

There is a systemd unit file in config/arscca-twisted.service


### Install Packages from requirements.txt

    env/bin/pip install -r requirements.txt


### Slack Integration

You will probably want to set the slack url in config/environment.txt

    cd /path/to/project
    cd config
    cp environment.txt-EXAMPLE environment.txt
    vi environment.txt


Run
---

Run as www-data so you have write access to the archive dir

    sudo -u www-data env/bin/python run.py



Test Slack Integration
----------------------

    env/bin/python util.py



Development Files
-----------------

The files index.html and index-log-delta.html were used in the development process
and are no longer needed. You may want to keep them around in case something breaks.
They work somewhat like a test-in-a-box.


Performance
-----------

If you are hosting this on a T2 or T3 instance on AWS, note that these instance
types are CPU burstable. That means it will appear performant when you parse
a single event, but if you turn on bin/demo_cp and let it run for a long time,
your CPU burst credits may run out.

On a t2.nano, which has a baseline rate of 5%, it takes about 15 seconds to parse a single event with 66 drivers.
When burst credits are available, it runs in about 400ms.

Supposedly burst credits go away on restart, so if you want to see baseline performance,
you may simply restart the box.

### Timeout POSTing to Upstream

If you are seeing timeouts POSTing to arscca-pyrame, it may be that you have run out
of burst credits.

### ssh Performance

Note that when you have no CPU burst credits available, it also takes longer
to do things like ssh into the box, open documents in vim, etc.


Backlog
-------

  -
