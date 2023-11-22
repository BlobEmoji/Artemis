from PIL import Image, ImageDraw, ImageFont


Color = tuple[int, int, int]

MAIN_BACKGROUND: Color = (242, 178, 82)
SECONDARY_BACKGROUND: Color = (227, 167, 77)
TEXT: Color = (243, 242, 247)

FONT: ImageFont.ImageFont = ImageFont.load_default(20)


def create_plaque(username: str, prompt_name: str, prompt_idx: int) -> Image.Image:
    username = f'@{username}'
    prompt_text: str = f'"{prompt_name}" (#{prompt_idx})'

    width: int = int(max(FONT.getlength(username), FONT.getlength(prompt_text))) + 100

    image = Image.new('RGB', (width, 100), color=MAIN_BACKGROUND)

    for text, y_pos in [(username, 35), (prompt_text, 65)]:
        draw = ImageDraw.Draw(image)
        draw.text((width / 2, y_pos), text, fill=TEXT, anchor='ms', font=FONT)

    return image
