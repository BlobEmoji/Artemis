from PIL import Image, ImageDraw, ImageFont


Color = tuple[int, int, int]

MAIN_BACKGROUND: Color = (255, 255, 255)
SECONDARY_BACKGROUND: Color = (214, 237, 245)
TEXT: Color = (44, 85, 209)

TEXT_HEIGHT: int = 36

FONT = ImageFont.truetype('/usr/share/fonts/dejavu/DejaVuSans.ttf', size=TEXT_HEIGHT)
BOLD_FONT = ImageFont.truetype('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf', size=TEXT_HEIGHT)

TRIANGLE_SLOPE: float = 3


def create_plaque(lines: list[str], bold_lines: list[int] = []) -> Image.Image:
    image: Image.Image = Image.new('RGB', (int(max(map(FONT.getlength, lines)) + 100), (len(lines) + 2) * TEXT_HEIGHT), color=MAIN_BACKGROUND)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)

    image_middle: float = image.width / 2

    triangle_width: float = image.height / TRIANGLE_SLOPE
    triangle_start_x: float = image_middle - triangle_width / 2
    triangle_end_x: float = image_middle + triangle_width / 2

    # Triangle across the middle
    draw.polygon([(triangle_start_x, 0), (triangle_end_x, 0), (triangle_end_x, image.height)], fill=SECONDARY_BACKGROUND)

    draw.rectangle(((triangle_end_x, 0), (image.width, image.height)), fill=SECONDARY_BACKGROUND)

    for line_number, text in enumerate(lines):
        y_pos: float = image.height * (line_number + 1) / (1 + len(lines))

        font = BOLD_FONT if line_number in bold_lines else FONT
        draw.text((image.width / 2, y_pos), text, fill=TEXT, anchor='mm', font=font)

    return image
