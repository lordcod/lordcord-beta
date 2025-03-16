import contextlib
from functools import lru_cache
import os
import random
import shutil
import string
import googletrans
import orjson
from typing import Optional, Dict, List


try:
    from bot.resources.ether import Emoji
except ImportError:
    Emoji = None

config = {}
default_languages = ["da", "de", "en", "es", "fr",  "pl", "ru", "tr"]
memoization_dict = {}
resource_dict = {}

translator = googletrans.Translator()


class DictMissing(dict):
    def __missing__(self, key: str) -> str:
        return '{'+key+'}'


def translate(text, dest, src='auto'):
    return translator.translate(text, dest, src).text


def _load_file(filename: str) -> bytes:
    with open(filename, "rb") as f:
        return f.read()


def _parse_json(content: str | bytes) -> dict:
    return orjson.loads(content)


def add_res_translation(key: str, value: str, locale: str):
    resource_dict.setdefault(locale, {})
    data = resource_dict[locale]
    data_keys = key.split(".")
    for num, tk in enumerate(data_keys, start=1):
        if num >= len(data_keys):
            data[tk] = value
            break
        if not isinstance(data.get(tk), dict):
            data[tk] = {}
        data = data[tk]


def add_translation(
    key: str,
    value: str,
    locale: Optional[str] = None
) -> None:
    locale = locale or config.get("locale")
    memoization_dict.setdefault(locale, {})
    memoization_dict[locale][key] = value
    add_res_translation(key, value, locale)


def add_dict_translations(path: str, data: Dict[str, str]):
    for loc, text in data.items():
        add_translation(path, text, loc)


def translate_dict(src: str, dest: str, src_dict: dict) -> dict:
    dest_dict = {}
    for key, value in src_dict.items():
        if isinstance(value, dict):
            dest_dict[key] = translate_dict(src, dest, value)
        elif isinstance(value, list):
            for num, text in enumerate(value):
                dest_dict.setdefault(key, [])
                dest_dict[key][num] = translate(
                    text, dest, src)
        else:
            dest_dict[key] = translate(value, dest, src)
    return dest_dict


def translation_with_languages(locale: str, text: str, languages: List[str]) -> dict:
    data = {}
    data[locale] = text

    if locale in languages:
        languages.remove(locale)

    for dest in languages:
        tran_text = translate(text, dest)
        data[dest] = tran_text

    return data


def _parser_foo_any_locales(locale: str, data: dict, new_data: dict):
    for key, value in data.items():
        if isinstance(value, dict):
            if not isinstance(new_data.get(key), dict):
                new_data[key] = {}
            _parser_foo_any_locales(locale, value, new_data[key])
        else:
            if not isinstance(new_data.get(key), dict):
                new_data[key] = {}
            new_data[key][locale] = value


def to_any_locales() -> dict:
    new_data = {}
    for loc, data in resource_dict.items():
        _parser_foo_any_locales(loc, data, new_data)
    return new_data


def to_i18n_translation(data: dict, path: Optional[str] = None) -> None:
    for key, value in data.items():
        if set(default_languages) & set(value.keys()):
            add_dict_translations(f"{path+'.' if path else ''}{key}", value)
        else:
            to_i18n_translation(value, f"{path+'.' if path else ''}{key}")


def from_folder(foldername: str) -> None:
    for filename in os.listdir(foldername):
        if not filename.endswith(".json"):
            continue
        filecontent = _load_file(f"{foldername}/{filename}")
        json_resource = _parse_json(filecontent)
        resource_dict[filename[:-5]] = json_resource
        parser(json_resource, filename[:-5])


def to_folder(foldername: str) -> str:
    for lang, data in resource_dict.items():
        with open(f"{foldername}/{lang}.json", "+wb") as file:
            jsondata = orjson.dumps(data)
            file.write(jsondata)


def from_file(filename: str) -> None:
    filecontent = _load_file(filename)
    json_resource = _parse_json(filecontent)
    for lang, data in json_resource.items():
        parser(data, lang)


def to_file(filename: str) -> str:
    jsondata = orjson.dumps(resource_dict)
    with open(filename, 'wb+') as file:
        file.write(jsondata)


def to_zip(filename: str) -> str:
    import shutil
    import os
    dirname = '_temp_localization_' + \
        ''.join([random.choice(string.hexdigits) for _ in range(4)])
    os.mkdir(dirname)

    filecontent = _load_file(filename)
    json_resource = _parse_json(filecontent)
    for lang, data in json_resource.items():
        with open(f'{dirname}/{lang}.json', 'wb+') as file:
            file.write(orjson.dumps(data))

    shutil.make_archive('localization', 'zip', dirname)
    for lang in json_resource.keys():
        os.remove(f'{dirname}/{lang}.json')
    os.rmdir(dirname)


category_names = {
    'mods': ['captcha', 'clone-role', 'delcat', 'errors', 'giveaway', 'purge', 'tempban', 'temprole'],
    'main': ['activiti', 'basic', 'bot-info', 'help', 'ideas', 'interaction', 'music', 'reminder', 'tempvoice', 'tickets', 'translate']
}


@lru_cache()
def get_category(path) -> str:
    for category, names in category_names.items():
        if path in names:
            return category
    print('not found category for path', path)
    return input('> ')


def to_folders(folder_name: str, lang: str):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)

    for path, value in memoization_dict[lang].items():
        pathes: list[str] = path.split('.')

        if pathes[0] in ('settings', 'economy'):
            folder_path = os.path.join(folder_name, pathes[0])
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)

            file_path = os.path.join(folder_path, pathes[1]+'.json')
        else:
            folder_path = os.path.join(folder_name, get_category(pathes[0]))
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)

            file_path = os.path.join(folder_path, pathes[0]+'.json')

        if not os.path.exists(file_path):
            open(file_path, 'x').close()

        with open(file_path, 'rb+') as file:
            data = file.read()

        if data:
            data = orjson.loads(data)
        else:
            data = {}

        data[path] = value

        with open(file_path, 'wb+') as file:
            file.write(orjson.dumps(data))


def parser(
    json_resource: dict,
    locale: Optional[str] = None,
    prefix: Optional[str] = None,
) -> None:
    for key, value in list(json_resource.items()):
        if isinstance(value, dict):
            parser(
                value,
                locale,
                f"{prefix+'.' if prefix else ''}{key}"
            )
        else:
            add_translation(
                f"{prefix+'.' if prefix else ''}{key}",
                value,
                locale
            )


def get(path: str):
    lang = config.get('locale')
    return memoization_dict[lang][path]


def get_dict(path: str, lang_mapping: Optional[dict] = None):
    data = {}

    for lang in default_languages:
        with contextlib.suppress(KeyError):
            text = memoization_dict[lang][path]
            lang = lang_mapping.get(lang, lang)
            data[lang] = text

    return data


def t_dict(path: str, mapping: Optional[dict] = None, **kwargs):
    data = {}

    for lang in default_languages:
        text = t(lang, path, mapping, **kwargs)
        data[lang] = text

    return data


def t(locale: Optional[str] = None, path: Optional[str] = None, mapping: Optional[dict] = None, **kwargs) -> str:
    if path is None:
        return ''

    lang = locale

    if locale not in memoization_dict or path not in memoization_dict[locale]:
        locale = config.get("locale")

    try:
        data = memoization_dict[locale][path]
    except KeyError:
        return f'{lang}.{path}'

    if not data:
        return data

    kwargs['Emoji'] = Emoji
    if mapping is not None:
        kwargs.update(mapping)

    return data.format_map(DictMissing(kwargs))


if __name__ == "__main__":
    shutil.make_archive('ideas', 'zip', 'ideas')

    # from_file("./bot/languages/localization_any.json")

    # for lang in ['es', 'pl']:
    #     memoization_dict[lang]['music.selector.placeholder'] = memoization_dict[lang].pop('music-selector.placeholder')
    #     if lang == 'en':
    #         continue
    #     to_folders(f'languages/{lang}', lang)

    # load i18n key
    # filecontent = _load_file("./bot/languages/localization_any.json")
    # json_resource = _parse_json(filecontent)
    # for lang in json_resource:
    #     print(lang)
    #     data = json_resource[lang]
    #     parser(data, lang, loadable=False)

    # to_zip("./bot/languages/localization_any.json")

    # for key, value in _parse_json(_load_file("add_temp_loc_ru.json")).items():
    #     add_translation(key, value, 'ru')
    # for key, value in _parse_json(_load_file("add_temp_loc_en.json")).items():
    #     add_translation(key, value, 'en')

    # with open(r'bot\languages\localization_any.json', 'wb') as file:
    # file.write(orjson.dumps(memoization_dict))

    # for locale, data in _parse_json(_load_file(("./bot/languages/localization.json"))).items():
    #     with open(f'localization/{locale}.json', 'wb+') as file:
    #         file.write(orjson.dumps(data))

    # with open('bot/languages/temp_loc.json', 'rb') as file:
    #     dataloc = orjson.loads(file.read())
    #     for loc, data in dataloc.items():
    #         parser(data, loc, loadable=False)

    # Translation dict
    # for lang in default_languages:
    #     if lang == "en":
    #         continue
    #     print(lang)
    #     trd = translate_dict(
    #         "en", lang, resource_dict['en']['delcat'])
    #     print(trd)
    #     parser(trd, lang, "delcat", loadable=False)

    # Translate to default languages
    # data = translation_with_languages(
    #     "ru", "Команда для начала игры в блэкджек. Игроки должны ставить ставки и пытаться набрать 21 очко, обыгрывая дилера.",
    #     default_languages)
    # print(orjson.dumps(data).decode())

    # Translation to default languages and added
    # add_dict_translations(
    #     "settings.module-name.role-reactions", translation_with_languages("en", "Reaction Roles", default_languages))

    # To any locales format
    # data = to_any_locales()
    # with open("test_loc.json", "+wb") as file:
    #     jsondata = orjson.dumps(data)
    #     file.write(jsondata)

    # To i18n format as any locales format
    # to_i18n_translation(_parse_json(_load_file("test_loc.json")))

    # to_file("localization_test.json")
