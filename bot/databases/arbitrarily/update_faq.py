from _connection import connection
import asyncio

id = 1178294479267045466


async def main():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tickets FROM guilds WHERE id = %s",
            (id,)
        )

        val = cursor.fetchone()
        data = val[0]
        print(data[1261496777220161631])

        data[1261496777220161631]['modals'] = [
            {
                "label": "Введите свой ник в роблоксе",
                "placeholder": "Убедитесь, что это уникальный ник, а не дисплей.",
                "style": 1
            },
            {'label': 'Что у вас произошло?',
                'placeholder': 'Расскажите максимально подробно', 'style': 2}
        ]
        data[1261496777220161631]['categories'].append({
            'label': 'Разбан',
            'emoji': '🔓',
            'description': 'Если вас забанили в игре. Нажмите сюда.'
        })
        data[1261496777220161631]['faq']['items'].append(
            {
                'label': 'У меня пропали деньги и машины?',
                'emoji': '😡',
                'response': 'В связи с обновлением базы данных, все деньги и автомобили были сброшены. Если вы что-то потеряли после обновления, то обратитесь в ticket.'
            }
        )

        cursor.execute(
            "UPDATE guilds SET tickets = %s WHERE id = %s", (data, id))

asyncio.run(main())
connection.close()
print("Finish")
