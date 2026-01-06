#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE products;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE orders;"

echo "Databases created successfully!"