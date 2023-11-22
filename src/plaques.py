from PIL import Image, ImageDraw, ImageFont


Color = tuple[int, int, int]

MAIN_BACKGROUND: Color = (242, 178, 82)
SECONDARY_BACKGROUND: Color = (227, 167, 77)
TEXT: Color = (243, 242, 247)

TEXT_HEIGHT: int = 36
FONT = ImageFont.truetype('/usr/share/fonts/dejavu/DejaVuSans.ttf', size=TEXT_HEIGHT)


def create_plaque(lines: list[str]) -> Image.Image:
    image: Image.Image = Image.new('RGB', (int(max(map(FONT.getlength, lines)) + 100), (len(lines) + 2) * TEXT_HEIGHT), color=MAIN_BACKGROUND)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)

    for line_number, text in enumerate(lines, start=1):
        y_pos: float = image.height * line_number / (1 + len(lines))

        draw.text((image.width / 2, y_pos), text, fill=TEXT, anchor='mm', font=FONT)

    return image
