import re
from typing import Any, Dict, List, Optional, Tuple

import orjson

from .misc import flatten_dict


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
            return str(self.context.get(var)) == self._strip_quotes(val)
        elif '!=' in condition:
            var, val = map(str.strip, condition.split('!=', 1))
            return str(self.context.get(var)) != self._strip_quotes(val)
        else:
            return bool(self.context.get(condition))

    def _parse_variable_with_default(self, result: str) -> Tuple[str, Optional[str]]:
        """Извлекает переменную и дефолтное значение из выражения"""
        if '||' in result:
            value, default = map(self._strip_quotes, result.split('||', 1))
            return value.strip(), default.strip()
        return self._strip_quotes(result).strip(), None

    def _strip_quotes(self, text: str) -> str:
        """Удаляет кавычки и пробелы"""
        return text.strip().strip('"\'') if isinstance(text, str) else text


class LordTemplate:
    REGEXP_FORMAT = re.compile(r'{([^{}]+)}')

    def findall(self, string: str) -> List[Tuple[str, str]]:
        return [(match.group(0), match.group(1)) for match in self.REGEXP_FORMAT.finditer(string)]

    def parse_key(self, var: str) -> Tuple[str, Optional[str]]:
        parts = [part.strip() for part in var.split('|', 1)]
        return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], None)

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
            key, default = self.parse_key(var)
            value = self.get_value(key, forms)

            if isinstance(value, dict):
                result[original] = default
            elif value not in (None, '', []):
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
