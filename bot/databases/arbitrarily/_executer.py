from _connection import connection


def execute(query, vars=None):
    with connection.cursor() as cursor:
        cursor.execute(query, vars)

        print('Finish')
