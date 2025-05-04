from typing import List, Optional



def param(attr: str, flags: Optional[List[str] | str] = None, default: Optional[str] = None):
    attr = str(attr)
    ret = '{'+attr

    if flags is not None:
        flags = [flags] if isinstance(flags, str) else flags
        for flag in flags:
            ret += '?&'+flag
    if default is not None:
        ret += f' | {default}'

    return ret+'}'


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
