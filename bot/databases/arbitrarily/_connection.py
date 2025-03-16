import os
import psycopg2
import sys

sys.path.append(os.getcwd())


try:
    from bot.databases.config import (host, port, user, password, db_name)

    connection = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name,
    )
    connection.autocommit = True
except Exception as err:
    print(type(err))
    print(err)
    exit()
