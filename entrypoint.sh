#!/bin/sh
echo "0.0.0.0       mysite.com" >> /etc/hosts
exec "$@"