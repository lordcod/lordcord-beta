from _executer import execute
import orjson

guild_id = 1179069504186232852
value = "[1178294479283814421]"
execute(
    """
            UPDATE
                guilds
            SET
                auto_roles = %s
            WHERE
                id = %s
        """,
    (value, guild_id, )
)

# value = orjson.dumps([
#     {"role_id": 1213860890395287653, "amount": 100, "name": "Green"},
#     {"role_id": 1213860899300053003, "amount": 200, "limit": 5},
#     {"role_id": 1213860908896624731, "amount": 300},
#     {"role_id": 1213860917734023210, "amount": 400},
#     {"role_id": 1213860926629879861, "amount": 500, "name": "Green + Blue"}
# ]).decode()
# execute(
#     """
#             UPDATE
#                 guilds
#             SET id = 1179069504186232852, ideas = %s
#             WHERE
#                 id = %s
#         """,
#     (data, guild_id, )
# )

# value = orjson.dumps([
#     {"role_id": 1213860890395287653, "amount": 100, "name": "Green"},
#     {"role_id": 1213860899300053003, "amount": 200, "limit": 5},
#     {"role_id": 1213860908896624731, "amount": 300},
#     {"role_id": 1213860917734023210, "amount": 400},
#     {"role_id": 1213860926629879861, "amount": 500, "name": "Green + Blue"}
# ]).decode()
# execute(
#     f"""
#         UPDATE guilds
#         SET economic_settings = jsonb_set(economic_settings ::jsonb, '{{shop}}', %s)
#         WHERE id = %s
#     """,
#     (value, guild_id, )
# )
