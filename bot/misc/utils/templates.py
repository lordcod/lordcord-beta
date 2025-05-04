import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import orjson

available_flags: Dict[str, Callable[[str], str]] = {
    'upper': lambda s: s.upper(),
    'lower': lambda s: s.lower(),
    'quote': lambda s: s.replace('"', '\\"').replace('\n', '\\n')
}

def _strip_quotes(text: str) -> str:
    """Удаляет кавычки и пробелы"""
    return text.strip().strip('"\'') if isinstance(text, str) else text

def flatten_dict(data: dict, prefix: str = ''):
    new_data = {}
    for k, v in data.items():
        if isinstance(v, dict):
            new_data.update(flatten_dict(v, prefix + k + '.'))
        else:
            new_data[prefix + k] = v
    return new_data


class ExpressionTemplate:
    def __init__(self, context: dict):
        self.context = flatten_dict(context)

    def render(self, template: str) -> str:
        """Основной метод рендеринга шаблона"""
        pattern = r'{%\s*(.*?)\s*=>\s*(.*?)\s*%}'
        return re.sub(pattern, self._process_match, template)

    def _process_match(self, match: re.Match) -> str:
        """Обработка выражения {% условие => значение || дефолт %}"""
        condition, result = match.groups()
        value, default = self._parse_variable_with_default(result)

        return (
            str(value)
            if self._eval_condition(condition)
            else default or ''
        )

    def _eval_condition(self, condition: str) -> bool:
        """Оценивает логическое условие"""
        condition = condition.strip()

        if '==' in condition:
            var, val = map(str.strip, condition.split('==', 1))
            return str(self.context.get(var)) == _strip_quotes(val)
        elif '!=' in condition:
            var, val = map(str.strip, condition.split('!=', 1))
            return str(self.context.get(var)) != _strip_quotes(val)
        else:
            return bool(self.context.get(condition))

    def _parse_variable_with_default(self, result: str) -> Tuple[str, Optional[str]]:
        """Извлекает переменную и дефолтное значение из выражения"""
        if '||' in result:
            value, default = map(_strip_quotes, result.split('||', 1))
            return value, default
        return _strip_quotes(result), None

class LordTemplate:
    REGEXP_FORMAT = re.compile(
        r'{\s*([a-zA-Z0-9\.\-=_]+(?:\?&[a-zA-Z0-9]+)*)(?:\s*\|\s*([^{}]*))?\s*}'
    )
    
    
    def findall(self, string: str) -> List[Tuple[str, str]]:
        return [(match.group(0), f"{match.group(1)}{' | ' + match.group(2) if match.group(2) else ''}") 
                for match in self.REGEXP_FORMAT.finditer(string)]


    def execute_flags(self, value: str, flags: List[str]):
        for flag in flags:
            execute = available_flags.get(flag)
            if execute is None:
                continue
            value = execute(value)
        return value

    def parse_flag(self, name: str):
        pattern = r'(\?&([a-zA-Z0-9]|\?&)+)$'
        flags = []

        results = re.findall(pattern, name)
        if results:
            flags = list(filter(bool, results[0][0].split('?&')))
            name = name.removesuffix(results[0][0])
        return name, flags

    def parse_key(self, var: str) -> Tuple[str, Optional[str]]:
        name, *default = [part.strip() for part in var.split('|', 1)]
        if len(default) == 0:
            default = None
        else:
            default = _strip_quotes(default[0])
        name, flags = self.parse_flag(name)
        return name, default, flags

    def get_value(self, key: str, data: Dict[str, Any]) -> Any:
        if key in data:
            return data[key]
        parts = key.split('.')
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                break
        return value

    def parse_value(self, variables: List[Tuple[str, str]], forms: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for original, var in variables:
            key, default, flags = self.parse_key(var)
            value = self.get_value(key, forms)

            if isinstance(value, dict):
                result[original] = default
            elif value not in (None, '', []):
                value = self.execute_flags(value, flags)
                result[original] = value
            else:
                result[original] = default
        return result

    def render(self, template: str, data: Dict[str, Any]) -> str:
        variables = self.findall(template)
        values = self.parse_value(variables, data)
        for original, replacement in values.items():
            template = template.replace(original, str(
                replacement) if replacement is not None else '')
        return template


def lord_format(string: Any, forms: dict) -> str:
    if not isinstance(string, str):
        string = orjson.dumps(string).decode()
    string = ExpressionTemplate(forms).render(string)
    result = LordTemplate().render(string, forms)
    return result


if __name__ == "__main__":
    exp = LordTemplate()
    content = "Категория запроса: { ticket.category.name?&upper?&lower?&quote | okey } ℹ️"
    res = exp.render(content, {'ticket.category.nam': 'test "" cat'})
    print(res)
