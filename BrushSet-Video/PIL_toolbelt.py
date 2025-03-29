from PIL import Image, ImageDraw, ImageFont

font_cache = {}

def get_font(font_name, font_size):
	if (font_name, font_size) in font_cache:
		font = font_cache[(font_name, font_size)]
	else:
		try:
			font = ImageFont.truetype(font_name, font_size)
		except IOError:
			font = ImageFont.load_default(size=font_size)
		font_cache[(font_name, font_size)] = font
	return font

size_cache = {}

def textsize(text, font=None, font_name=None, font_size=None, spacing=4, stroke_width=0):
	"""
	text: str
	font: ImageFont
	font_name: str
	font_size: int
	spacing: int

	returns: (width, height)
	"""
	if font and (font, text) in size_cache:
		return size_cache[(font, text)]
	elif font is None and (font_name, font_size, text) in size_cache:
		return size_cache[(font_name, font_size, text)]

	if font is None:
		font = ImageFont.truetype(font_name, font_size)

	im = Image.new(mode="P", size=(0, 0))
	draw = ImageDraw.Draw(im)
	_, _, width, height = draw.textbbox((0, 0), text=text, font=font, spacing=spacing, stroke_width=stroke_width)
	return width, height




def crop_n_resize(image_path, video_width, video_height):
    """
    Process the image to fit within a horizontal or vertical video frame.
    Center-crop and resize using aspect ratio and Lanczos resampling.
    """
    img = Image.open(image_path)
    img_width, img_height = img.size
    img_aspect_ratio = img_width / img_height
    video_aspect_ratio = video_width / video_height

    if img_aspect_ratio > video_aspect_ratio:  # Image is wider than the video
        # Fit height to the video and crop excess width
        scale_factor = video_height / img_height
        new_width = int(img_width * scale_factor)
        new_height = video_height
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        # Crop the center horizontally
        left = (new_width - video_width) // 2
        right = left + video_width
        img_cropped = img_resized.crop((left, 0, right, new_height))
    else:  # Image is taller (or same ratio) than the video
        # Fit width to the video and crop excess height
        scale_factor = video_width / img_width
        new_width = video_width
        new_height = int(img_height * scale_factor)
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        # Crop the center vertically
        top = (new_height - video_height) // 2
        bottom = top + video_height
        img_cropped = img_resized.crop((0, top, new_width, bottom))

    return img_cropped
