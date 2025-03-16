

class DatePluralRussia:
    @staticmethod
    def plural(numbers: int, forms: list[str]) -> str:
        idx = None
        if numbers % 10 == 1 and numbers % 100 != 11:
            idx = 0
        elif numbers % 10 >= 2 and numbers % 10 <= 4 and (
                numbers % 100 < 10 or numbers % 100 >= 20):
            idx = 1
        else:
            idx = 2
        return f"{numbers} {forms[idx]}"

    @staticmethod
    def years(timestamp: int):
        forms = ['год', 'года', 'лет']
        return DatePluralRussia.plural(timestamp, forms)

    @staticmethod
    def months(timestamp: int):
        forms = ['месяц', 'месяца', 'месяцов']
        return DatePluralRussia.plural(timestamp, forms)

    @staticmethod
    def days(timestamp: int):
        forms = ['день', 'дня', 'дней']
        return DatePluralRussia.plural(timestamp, forms)

    @staticmethod
    def hours(timestamp: int):
        forms = ['час', 'часа', 'часов']
        return DatePluralRussia.plural(timestamp, forms)

    @staticmethod
    def minutes(timestamp: int):
        forms = ['минута', 'минуты', 'минут']
        return DatePluralRussia.plural(timestamp, forms)

    @staticmethod
    def seconds(timestamp: int):
        forms = ['секунда', 'секунды', 'секунд']
        return DatePluralRussia.plural(timestamp, forms)

    @staticmethod
    def convertor(timestamp: int, great: str):
        method = getattr(DatePluralRussia, great)
        return method(timestamp)


def convert_dataplural_english(timestamp: int, great: str):
    if timestamp == 1:
        return f"{timestamp} {great.rstrip('s')}"
    return f"{timestamp} {great}"


distributing = {
    'ru': DatePluralRussia.convertor,
    'en': convert_dataplural_english
}


def time_convert(timestamp: (int | float)) -> dict[str, int]:
    return {
        "years": int(timestamp / 31_579_200),
        "months": int(timestamp / 2_631_600 % 12),
        "days": int(timestamp / 86_400 % 30),
        "hours": int(timestamp / 3_600 % 24),
        "minutes": int(timestamp / 60 % 60),
        "seconds": int(timestamp % 60)
    }


def display_time(number: int, lang: str = "en", max_items: int = 3, with_rounding: bool = False) -> str:
    if number == 0:
        return distributing.get(lang, distributing['en'])(0, 'seconds')
    if number % 10 != 0:
        number = round(number + 5, -1)

    func = distributing.get(lang, distributing['en'])

    current_time = time_convert(number)
    current_time = {key: num
                    for key, num in current_time.items()
                    if num != 0}

    if with_rounding:
        if max_items > len(current_time):
            index = list(current_time.keys())[len(current_time)-1]
            current_time[index] += 1
        else:
            index = list(current_time.keys())[max_items-1]
            current_time[index] += 1

    time_strings = [func(num, key)
                    for key, num in current_time.items()]

    return ", ".join(time_strings[:max_items])


if __name__ == '__main__':
    import sys
    while True:
        num = eval(input('> '), {}, {})

        if num % 10 != 0:
            number = round(num + 5, -1)
        else:
            number = num
        print(number, num, round(num + 5, -1))

        print(display_time(num, *sys.argv[1:]))
