#!/usr/bin/env python

import re
import os
from pathlib import Path
import traceback
from PIL import Image
from PIL.ImageOps import invert
from subprocess import run
from shutil import copyfile, make_archive, copytree
from tempfile import TemporaryDirectory
# Procreate brushes require an inverted image

here = Path(__file__).parent

indir = Path(here)/"Samples.tmp"
outdir = Path(here)/"build"
template = Path(here)/"template"

os.makedirs(outdir, exist_ok=True)
os.makedirs(indir, exist_ok=True)
os.makedirs(template, exist_ok=True)

outdir.mkdir(exist_ok=True)


from PIL import Image, ImageDraw, ImageFilter, ImageOps, Image
import numpy as np

def center_crop_to_ratio(image, target_ratio):
    """
    Crop the image to match the target aspect ratio while preserving the center.
    
    Parameters:
        image (PIL.Image): The input image.
        target_ratio (float): The desired aspect ratio (width/height).
        
    Returns:
        PIL.Image: The center-cropped image.
    """
    img_width, img_height = image.size
    img_ratio = img_width / img_height
    if img_ratio > target_ratio:
        # Image is wider than target ratio: crop width
        new_width = int(img_height * target_ratio)
        left = (img_width - new_width) // 2
        crop_box = (left, 0, left + new_width, img_height)
    else:
        # Image is taller than target ratio: crop height
        new_height = int(img_width / target_ratio)
        upper = (img_height - new_height) // 2
        crop_box = (0, upper, img_width, upper + new_height)
    return image.crop(crop_box)

def create_radial_mask(width, height):
    """
    Create a radial gradient mask with transparency 0 at the edges and 255 at the center.
    
    Parameters:
        width (int): Width of the mask.
        height (int): Height of the mask.
        
    Returns:
        PIL.Image: A grayscale (L mode) image representing the alpha mask.
    """
    # Create coordinate grid
    x = np.linspace(0, width - 1, width)
    y = np.linspace(0, height - 1, height)
    x_grid, y_grid = np.meshgrid(x, y)
    
    # Calculate distance from center
    center_x, center_y = width / 2, height / 2
    distance = np.sqrt((x_grid - center_x) ** 2 + (y_grid - center_y) ** 2)
    max_distance = np.sqrt(center_x ** 2 + center_y ** 2)
    
    # Normalize and invert distances to get alpha values (center opaque, edges transparent)
    normalized = distance / max_distance
    alpha = (1 - normalized) * 255
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    
    return Image.fromarray(alpha, mode="L")

def process_image(input_path, output_path, target_width, target_height):
    """
    Process the input image by cropping, resizing, and applying a radial transparency mask.
    
    Parameters:
        input_path (str): Path to the input JPEG image.
        output_path (str): Path where the output PNG image will be saved.
        target_width (int): Desired width of the output image.
        target_height (int): Desired height of the output image.
    """
    target_ratio = target_width / target_height
    
    # Open the source image
    if isinstance(input_path, Image.Image):
        image = input_path
    else:
        image = Image.open(input_path)
    
    # Crop the image to the target aspect ratio
    cropped = center_crop_to_ratio(image, target_ratio)
    
    # Resize the cropped image to target dimensions
    resized = cropped.resize((target_width, target_height), Image.LANCZOS)
    
    # Create the radial gradient alpha mask
    mask = create_radial_mask(target_width, target_height)
    
    # Convert to RGBA and apply the mask as the alpha channel
    result = resized.convert("RGBA")
    result.putalpha(mask)
    
    # Save the final image as PNG
    result.save(output_path)
    print(f"Processed image saved as {output_path}")

def remove_alpha(image):
    bkg = Image.new("RGB", image.size, (255, 255, 255))
    bkg.paste(image, mask=image.split()[3])
    return bkg


def generate_brush_set(brush_ids, set_name):
    """
    Generate folders with UUID folder name and then copy the brush zip contents into the folder.

    then create a brushset.plist file with data:
    <?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>brushes</key>
	<array>
		<string>1B47313A-17EA-45B8-830C-C910FF1E1601</string>
		<string>1B45948A-4D12-4D3D-8C49-C9833922F208</string>
        ...
	</array>
	<key>name</key>
	<string>Snake Texture</string>
</dict>
</plist>

    """


for f in indir.iterdir():
    m = re.fullmatch(r"(\d+)", f.stem)
    if m is None:
        continue
    brushid = m.group(1)

    outfn = f"{brushid}.brush"

    # with TemporaryDirectory() as tempdir:
    tempdir = "build/tmp"
    os.makedirs(tempdir, exist_ok=True)
    
    tempdir = Path(tempdir)


    # The "Brush.archive" file is a binary plist file that contains
    # settings. It should remain constant between brushes, but the
    # properties of all brushes can be modified in tandem (say,
    # to change the brush shape) by replacing this file.
    fn = 'Brush.archive'
    xml = open(template/fn, 'r').read()
    xml = xml.replace("PLACEHOLDER_NAME", f"{brushid}")
    plist = tempdir/fn
    with open(plist,'w') as _:
        _.write(xml)
    # The `plutil` command only exists on MacOS
    run(('plutil','-convert','binary1',plist))

    # Brush Grain image needs to be inverted so inked parts
    # are white.
    im = Image.open(f)
    try:
        im2 = invert(remove_alpha(im))
    except IndexError:
        # non-alpha image (no transparency)
        # image is in RGB mode, convert it to B&W
        im2 = im.convert("L")
    im2.save(tempdir/'Grain.png')

    
    # Create a thumbnail for the brush preview (using the same image as the brush grain and applying a gradient)
    qldir = tempdir/'QuickLook'
    qldir.mkdir(exist_ok=True, parents=True)
    process_image(im2, qldir/'Thumbnail.png', 1060, 324)


    # Copy Signature folder
    x = os.stat(template/'Signature')
    print(x)
    copytree(template/'Signature/', tempdir, dirs_exist_ok=True)

    # The `.brush` file is merely a renamed zip archive of the brush directory
    target = outdir/outfn
    if target.exists():
        target.unlink()
    if (outdir/(outfn+".zip")).exists():
        (outdir/(outfn+".zip")).unlink()

    make_archive(target, 'zip', tempdir)
    # Correct shutil weirdness
    (outdir/(outfn+".zip")).rename(target)

    print(brushid)

# make_archive("FGDC geology patterns (Procreate brushes)",'zip','build')

# run(('plutil', '-convert', 'xml1', "Expected/BrushFatboy.archive"))