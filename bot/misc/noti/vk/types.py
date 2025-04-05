from typing import List, TypedDict


class Attachment(TypedDict):
    type: str
    photo: dict


class Post(TypedDict):
    id: int
    owner_id: int
    from_id: int
    created_by: int
    date: int
    text: str
    reply_owner_id: int
    reply_post_id: int
    friends_only: int
    comments: dict
    copyright: dict
    likes: dict
    reposts: dict
    views: dict
    post_type: str
    post_source: dict
    attachments: List[Attachment]


class VkPost:
    def __init__(self, data: Post):
        self.text = data['text']
        self.photos = [
            for data['d']
        ]
