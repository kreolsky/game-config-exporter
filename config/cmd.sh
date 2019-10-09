#!/bin/bash
echo "Running Production Server"
exec uwsgi --ini /home/config/uwsgi.ini --http 0.0.0.0:80 --thunder-lock
