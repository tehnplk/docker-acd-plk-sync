#!/bin/sh
set -eu

/app/run-sync.sh
exec cron -f
