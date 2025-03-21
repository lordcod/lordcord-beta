# https://api.vk.com/method/groups.get?access_token=vk1.a.qsf7u3rKG27R5yijx_UwPzTlK5D5KixHOCBIwAk3mE8ZBq8QOtI4LL62FN4T14wNOLib5r46yF9WH861d0Dgv7siKrt9TDlFezXcjHkRJOHU3bRBPFy4_kTxF58RIFAMExF-rRP3_TSgbAjW1pjNlnT18fRlQv7TYp39Em8rKSVf_7kCmlJiiDug2b5gbuc-INrNdWRbdw4oQBCsVqW5NQ&v=5.101&filter=admin&extended=1&callback=__jp0
# https://api.vk.com/method/groups.getCallbackConfirmationCode?access_token=vk1.a.Ujsd2axSnz9XOONfahSCaDJSi0KtOYqzhaFMzh5cwJTSoOM4fkefK6iszZ-Wk7Z315geA3JnKLVZq3IapedPO52NNqIzwaSd7URRZ59rpGEhpaYCpTG_QiWYcnwkFmPPAkqOgxGvJmMfNTQAYEJNDe77A6tbaa5nVbrNQ6iHjDQ_QYWEpjhBY3aJnjdjt8HDIN0v2jgzgTanl3QbFqHUyw&v=5.101&group_id=222485128&callback=__jp1
# https://api.vk.com/method/groups.addCallbackServer?access_token=vk1.a.Ujsd2axSnz9XOONfahSCaDJSi0KtOYqzhaFMzh5cwJTSoOM4fkefK6iszZ-Wk7Z315geA3JnKLVZq3IapedPO52NNqIzwaSd7URRZ59rpGEhpaYCpTG_QiWYcnwkFmPPAkqOgxGvJmMfNTQAYEJNDe77A6tbaa5nVbrNQ6iHjDQ_QYWEpjhBY3aJnjdjt8HDIN0v2jgzgTanl3QbFqHUyw&v=5.101&group_id=222485128&url=https%3A%2F%2Fjuniper.bot%2Fvk%2Fcallback%2F36eb06d1-dece-4b7e-a005-f0c104ff2185&title=JuniperBot%2036&callback=__jp2
# https://api.vk.com/method/groups.setCallbackSettings?access_token=vk1.a.Ujsd2axSnz9XOONfahSCaDJSi0KtOYqzhaFMzh5cwJTSoOM4fkefK6iszZ-Wk7Z315geA3JnKLVZq3IapedPO52NNqIzwaSd7URRZ59rpGEhpaYCpTG_QiWYcnwkFmPPAkqOgxGvJmMfNTQAYEJNDe77A6tbaa5nVbrNQ6iHjDQ_QYWEpjhBY3aJnjdjt8HDIN0v2jgzgTanl3QbFqHUyw&v=5.101&group_id=222485128&server_id=7&api_version=5.101&wall_post_new=1&wall_repost=1&callback=__jp3


import random
from typing import Optional, Union
from aiohttp import ClientSession, ClientResponse
from string import hexdigits

SALT = ''.join([random.choice(hexdigits) for _ in range(15)])


class VkApiAuthException(Exception):
    def __init__(
        self,
        error: str,
        error_description: str,
        response: ClientResponse,
        *args
    ):
        self.error = error
        self.response = response
        super().__init__(error_description, *args)


class VkApiAuth:
    client_id: int
    redirect_uri: str
    session: ClientSession

    def __init__(
        self,
        client_id: int,
        redirect_uri: str,
        session: Optional[ClientSession] = None
    ):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.session = session

    def generate_code_challange(self, code: Union[str, bytes]):
        from hashlib import sha256
        from encodings.base64_codec import base64_encode
        if isinstance(code, str):
            code = code.encode()

        token = code+SALT.encode()
        hash = base64_encode(sha256(token).digest())[0].decode()
        return (
            hash
            .replace('/', '_')
            .replace('=', '')
            .replace('\u002B', '-')
            .replace('\n', '')
        )

    def get_auth_link(self, state: str):
        code_challenge = self.generate_code_challange(state)
        link = (
            "https://id.vk.com/authorize"
            "?response_type=code"
            f"&client_id={self.client_id}"
            "&scope=groups"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
            "&code_challenge_method=S256"
            f"&code_challenge={code_challenge}"
        )
        return link

    def get_auth_group_link(self, group_id: int):
        link = (
            "https://oauth.vk.com/authorize"
            "?response_type=token"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&group_ids={group_id}"
            "&v=5.101"
            "&display=popup"
            "&scope=manage"
        )
        return link

    async def verifi(self, state: str, device_id: str, code: str):
        url = "https://id.vk.com/oauth2/auth"
        data = {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'code_verifier': state+SALT,
            'code': code,
            'device_id': device_id,
            'redirect_uri': self.redirect_uri,
        }
        async with self.session.post(url, data=data) as response:
            response.raise_for_status()
            data = await response.json()

            if 'error' in data:
                raise VkApiAuthException(
                    data['error'], data['error_description'], response)
            return data


if __name__ == '__main__':
    vk_api_auth = VkApiAuth(
        51922313,
        'https://lordcord.xyz/vk-callback'
    )
    print(vk_api_auth.get_auth_link('random-state'))
