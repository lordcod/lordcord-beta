from typing import Optional
import nextcord


def get_info_dd(
    *,
    placeholder: Optional[str] = None,
    label: Optional[str] = None,
    description: Optional[str] = None,
    emoji: Optional[str] = None,
    default: Optional[bool] = None,
    disabled: Optional[bool] = None,
    row: Optional[int] = None,
):
    if placeholder is None and label is None:
        raise TypeError('Empty information')

    if default is None:
        default = label is not None

    if disabled is None:
        disabled = label is None

    options = []
    if label is not None:
        options.append(nextcord.SelectOption(
            label=label,
            description=description,
            emoji=emoji,
            default=default
        ))
    else:
        options.append(nextcord.SelectOption(label='SelectOption'))

    select = nextcord.ui.StringSelect(
        placeholder=placeholder,
        options=options,
        disabled=disabled,
        row=row
    )
    return select
