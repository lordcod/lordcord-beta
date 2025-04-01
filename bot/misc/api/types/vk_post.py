# https://dev.vk.com/ru/reference/objects/post

from typing import List


class VkPost:
    message: str
    attachments: List[str]

    def __init__(self, data: dict):
        self.message = data.get('text')
        self.attachments = [
            atch['photo']['orig_photo']['url']
            for atch in data['attachments']
            if atch['type'] == 'photo'
        ]
