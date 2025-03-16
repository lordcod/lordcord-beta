from _connection import connection
import orjson


def change_data(guild_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT command_permissions FROM guilds WHERE id = %s", (guild_id,))

        val = cursor.fetchone()[0]

    datas = {}
    for cmname, values in val.items():
        print(cmname, values)
        new_perms = {}

        for name, perm in values.get('distribution', {}).items():
            new_dict = {}
            new_names = {
                'cooldown': 'cooldown',
                'allow-role': 'allow-roles',
                'allow-channel': 'allow-channels',
            }

            if name == 'cooldown':
                new_dict = perm
            elif name == 'channels':
                new_dict["channels"] = perm.get('values')
            elif name == 'role':
                new_dict = perm.get('values')

            new_perms[new_names.get(name, name)] = new_dict

        datas[cmname] = {'distribution': new_perms}
        if values.get('operate') is not None:
            datas[cmname]['operate'] = values.get('operate')

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE guilds SET command_permissions = %s WHERE id = %s", (orjson.dumps(datas).decode(), guild_id,))


with connection.cursor() as cursor:
    cursor.execute(
        "SELECT id, command_permissions FROM guilds")
    values = cursor.fetchall()
    print(values)
    for id, command_permissions in values:
        if command_permissions:
            change_data(id)


print("Finish")
connection.close()
