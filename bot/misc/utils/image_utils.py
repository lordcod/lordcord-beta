# bot/misc/image_utils.py
import nextcord
from easy_pil import Editor, Font, load_image_async


async def generate_welcome_image(member: nextcord.Member, background_link: str) -> bytes:
    bot = member._state._get_client()
    session = bot.session

    background_image = await load_image_async(background_link, session=session)
    background = Editor(background_image).resize((800, 450))

    profile_image = await load_image_async(member.display_avatar.with_size(128).url, session=session)
    profile = Editor(profile_image).resize((150, 150)).circle_image()

    nunito = Font("assets/Nunito-ExtraBold.ttf", 40)
    nunito_small = Font("assets/Nunito-Black.ttf", 25)
    nunito_light = Font("assets/Nunito-Black.ttf", 20)

    background.paste(profile, (325, 90))
    background.ellipse((325, 90), 150, 150, outline=(
        125, 249, 255), stroke_width=4)

    add_gradient(background.image, nunito.font, f"WELCOME TO {member.guild.name.upper()}", 260,
                 (253, 187, 45), (34, 193, 195))

    background.text((400, 320), member.display_name,
                    color="#ff00a6", font=nunito_small, align="center")
    background.text((400, 360), f"You are the {member.guild.member_count}th Member",
                    color="#F5923B", font=nunito_light, align="center")

    return background.image_bytes
