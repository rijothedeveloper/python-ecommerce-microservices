##!/bin/sh
#set -e
#
#psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE products;"
#psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE orders;"
#
#echo "Databases created successfully!"


#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE products;
    CREATE DATABASE orders;

    GRANT ALL PRIVILEGES ON DATABASE products TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON DATABASE orders TO "$POSTGRES_USER";
EOSQL

echo "Databases created successfully!"