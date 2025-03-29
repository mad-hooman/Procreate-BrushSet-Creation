import os
import random
from typing import Dict, List
from moviepy.editor import *
import numpy as np
from scipy.integrate import cumulative_trapezoid as np_cumtrapz
from PIL import Image, ImageDraw, ImageFont
from PIL_toolbelt import textsize

import extract_brushes
import graph

# Configuration
SS = 1
screen_size = (595, 962)
image_size = (595, 184)
total_duration = 15  # seconds
paddingY = 10
fontSize = 20
ScrollingClipX = 248

SSscreen = (screen_size[0]*SS, screen_size[1]*SS)
SSimg = (image_size[0]*SS, image_size[1]*SS)
SSpaddingY = paddingY*SS
SSfontSize = fontSize * SS

ImageBGColor = (51, 48, 51)
OverAllBGColor = (42, 40, 40)
TextColor = (196, 193, 196)


def load_cover(cover_path, brush_name):
	"""
	load the image, no need to use SS here

	font file `Assets/NimbusSanL-Bol.otf`
	
	place the animated video at X=248 px, Y= 0 px
	place the text in the middle of X 18 to 208 px, Y = 180 px

	Text color is white,
	size from 14 to 20 px (based to text length, if the text size overflows 180px width, put ellipsis)
	"""

	# Load image
	img = Image.open(cover_path)

	name_font_size = 20

	# load font
	while True:
		font = ImageFont.truetype("Assets/NimbusSanL-Bol.otf", name_font_size)
		text_width, text_height = textsize(brush_name, font=font)
		if text_width <= 180:
			break

		if name_font_size == 14:
			# remove last 4 characters and add ellipsis
			brush_name = brush_name[:-4] + "..."
		else:
			name_font_size -= 1

	# Place the text in the middle of X 18 to 208 px, Y = 180 px
	textX = 18 + (190 - text_width) // 2
	textY = 180
	draw = ImageDraw.Draw(img)


	draw.text((textX, textY), brush_name, font=font, fill=TextColor)

	return img



def generate_thumbnail_to_brush(image_path:str, name:str, uuid:str):
	"""
	load the image,
	resize it to `image_size`,
	add the name as text using `Assets/AlmarenaNeue-Bold.otf` font place it at 20px,20px
	add a png `Assets/feather.png` on top right corner

	add rgb(24, 22, 25) as background color
	"""

	# Load image
	img = Image.open(image_path)
	img = img.resize(SSimg, Image.LANCZOS)

	# Create background
	background = Image.new("RGBA", img.size, ImageBGColor)
	# Paste image on background
	background.paste(img, (0, 0), img)
	img = background
	

	# Draw text
	draw = ImageDraw.Draw(img)
	font = ImageFont.truetype("Assets/AlmarenaNeue-Bold.otf", SSfontSize)
	# Calculate text size
	textX = 25*SS
	textY = 25*SS
	draw.text((textX, textY), name, font=font, fill=TextColor)

	# Add feather icon on top right corner (no resize)
	feather_icon = Image.open("Assets/feather.png")
	feather_size = feather_icon.size
	# Resize feather icon
	SSfeather_size = (feather_size[0]*SS, feather_size[1]*SS)
	feather_icon = feather_icon.resize(SSfeather_size, Image.LANCZOS)
	# Paste feather icon
	img.paste(feather_icon, (img.size[0] - SSfeather_size[0], 0), feather_icon)

	# make it rounded corners
	# Create a mask for rounded corners
	mask = Image.new("L", img.size, 0)
	draw_mask = ImageDraw.Draw(mask)
	radius = 20*SS
	draw_mask.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=radius, fill=255)
	# Apply the mask to the image
	img.putalpha(mask)
	
	# Save thumbnail with UUID
	uuid = uuid.replace("-", "_")
	# Create temporary directory for thumbnails
	os.makedirs("thumbnails.tmp", exist_ok=True)
	# Save thumbnail
	img.save(f"thumbnails.tmp/{name}-{uuid}.png")


	return img


def progress_bar(w, h):
	"""
	Just a simple rounded rectangle with a color of rgb(151, 149, 152)"""


def generate_video(images: List[Dict[str, str]], brush_name:str, output_file: str = "output.mp4"):
	"""
	Create a composite video by stitching together all thumbnail images in a long vertical image
	and scrolling it upward according to a segmented (looped) speed profile.
	"""
	# Generate random loop durations
	loop_times = random.randrange(6, 9)
	TimeLeft = total_duration
	avg_time = TimeLeft / loop_times

	loop_table = []
	for i in range(loop_times):
		time_for_this_loop = random.uniform(avg_time * 0.8, avg_time * 1.2)
		TimeLeft -= time_for_this_loop
		loop_table.append(time_for_this_loop)
		if TimeLeft <= 0:
			break

	total_loops = len(loop_table)
	# Compute cumulative time boundaries for each loop segment
	cumulative_loop_times = np.cumsum([0] + loop_table)  # e.g. [0, d1, d1+d2, ...]
	
	# Precompute the integrated (normalized) displacement profile for each loop.
	# For each loop, we treat its duration as T_local, and use nominal parameters.
	loop_integration = []
	for d in loop_table:
		num_samples = 1000
		t_vals_local = np.linspace(0, d, num_samples)
		# Use a nominal peak speed of 1.0 (it will be normalized later)
		v_vals_local = np.array([graph.speed_at_time(t, d, 1.0, 5, hold_fraction=0.1) for t in t_vals_local])
		# Use trapezoidal integration to get cumulative displacement
		cumulative_disp_local = np_cumtrapz(v_vals_local, t_vals_local, initial=0)
		total_disp_local = cumulative_disp_local[-1]
		loop_integration.append((t_vals_local, cumulative_disp_local, total_disp_local))
	
	# Compute total vertical displacement.
	total_list_height = len(images) * SSimg[1]
	start_y = 0
	end_y = -(total_list_height - SSscreen[1])  # scrolling upward

	# Define the multi-loop scrolling position function.
	def scroll_position(t_current):
		# Find which loop t_current falls in.
		if t_current >= cumulative_loop_times[-1]:
			loop_index = total_loops - 1
			local_time = loop_table[-1]
		else:
			# Find the segment such that cumulative_loop_times[i] <= t_current < cumulative_loop_times[i+1]
			loop_index = np.searchsorted(cumulative_loop_times, t_current, side='right') - 1
			local_time = t_current - cumulative_loop_times[loop_index]
		
		# Retrieve precomputed integration for the current loop.
		t_vals_local, cumulative_disp_local, total_disp_local = loop_integration[loop_index]
		local_fraction = (np.interp(local_time, t_vals_local, cumulative_disp_local) / 
						  total_disp_local) if total_disp_local else 0
		# Each loop contributes an equal share of the total displacement.
		overall_fraction = (loop_index + local_fraction) / total_loops
		return start_y + overall_fraction * (end_y - start_y)

	# Create a composite image that stitches all thumbnails vertically.
	composite_img = Image.new("RGBA", (SSscreen[0], total_list_height), (0,0,0,0))
	for idx, img_info in enumerate(images):
		thumb = generate_thumbnail_to_brush(img_info["path"], str(idx+1), img_info["uuid"])
		composite_img.paste(thumb, (0, idx * (SSimg[1] + SSpaddingY)))
	composite_np = np.array(composite_img)
	background_clip = ImageClip(composite_np).set_duration(total_duration)

	del composite_img
	del thumb
	del images

	# Set the scrolling animation with the multi-loop position updater.
	scrolling_clip = background_clip.set_position(lambda t: (ScrollingClipX, scroll_position(t)))
	
	# Create the final composite clip with the desired screen size.
	# final = CompositeVideoClip(
	# 	[scrolling_clip], 
	# 	size=SSscreen,
	# 	bg_color=OverAllBGColor
	# ).set_duration(total_duration)

	if SS != 1:
		scrolling_clip = scrolling_clip.resize(screen_size)

	# Add a cover image at the beginning
	cover_path = "Assets/MainCover.png"
	cover_img = load_cover(cover_path, brush_name)

	# put the video at X=248 px, Y= 0 px on the cover
	cover_clip = ImageClip(np.array(cover_img)).set_duration(total_duration)

	cover_clip = cover_clip.set_position((0, 0))
	cover_clip = cover_clip.set_duration(total_duration)

	# Set the cover image to be the background
	finalCovered = CompositeVideoClip(
		[cover_clip, scrolling_clip], 
		size=cover_clip.size, 
		bg_color=OverAllBGColor
	).set_duration(total_duration)



	temp_output = "temp_output.mp4"
	# Write the video file with high quality settings.
	finalCovered.write_videofile(
		temp_output,
		fps=60,
		threads=8,
		preset="ultrafast",
		ffmpeg_params=[
			"-crf", "18",
			"-profile:v", "high444",
			"-tune", "animation",
			"-x264-params", "bframes=8:ref=6"
		]
	)

	try:
		os.remove(output_file)
	except FileNotFoundError:
		pass

	# Rename the temporary output file to the final output file
	os.rename(temp_output, output_file)



if __name__ == "__main__":
	# Example usage
	for f in os.scandir("Brushsets.tmp"):
		if not f.name.endswith(".brushset"):
			continue
		if not f.is_file():
			continue


		brushset_file = f.path
		temp_dir = "Temp.tmp"
		thumbnails_dir = "thumbnails.tmp"
		output_dir = "output.tmp"

		os.makedirs(temp_dir, exist_ok=True)
		os.makedirs(thumbnails_dir, exist_ok=True)
		os.makedirs(output_dir, exist_ok=True)

		# Extract brushset information
		brushset_info = extract_brushes.extract_brushset_info(brushset_file, temp_dir)
		# Generate video
		generate_video(brushset_info["brushes"], brush_name=brushset_info["name"], output_file=f"{output_dir}/{brushset_info['name']}.mp4")
		# Clean up temporary files
		import shutil
		shutil.rmtree(temp_dir)
		shutil.rmtree(thumbnails_dir)

