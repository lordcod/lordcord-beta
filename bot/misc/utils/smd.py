from typing import Optional


def param(attr: str, default: Optional[str] = None):
    attr = str(attr)
    if default is None:
        return '{'+attr+'}'

    return '{'+attr+'|'+str(default)+'}'


def expression(attr: str, text: str, default: Optional[str] = None):
    attr = str(attr)
    text = str(text)
    default = default and str(default)

    if text.strip() != text:
        text = f'"{text}"'
    if default is not None and default.strip() != default:
        default = f'"{default}"'

    if default is None:
        return '{% ' + attr + ' => ' + text + ' %}'

    return '{% ' + attr + ' => ' + text + ' || ' + default + ' %}'
