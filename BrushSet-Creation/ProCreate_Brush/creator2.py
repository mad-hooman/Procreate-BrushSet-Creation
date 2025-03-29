import time
import uuid
from typing import List
#!/usr/bin/env python

import re
import os
import zipfile
from pathlib import Path
import traceback
from tempfile import TemporaryDirectory
from shutil import copyfile, make_archive, copytree
from subprocess import run
from PIL import Image
from PIL.ImageOps import invert
import xml.etree.ElementTree as ET
import numpy as np

here = Path(__file__).parent

indir = here/"Samples.tmp"
outdir = here/"build_brushes.tmp"
setdir = here/"build_brush_sets.tmp"
template = here/"template"

# Ensure directories exist
for dir in [indir, outdir, template, setdir]:
	dir.mkdir(exist_ok=True)

# Shared utility functions
def center_crop_to_ratio(image, target_ratio):
	"""Crop image to target aspect ratio while preserving center."""
	width, height = image.size
	current_ratio = width / height
	
	if current_ratio > target_ratio:
		new_width = int(height * target_ratio)
		left = (width - new_width) // 2
		return image.crop((left, 0, left + new_width, height))
	else:
		new_height = int(width / target_ratio)
		top = (height - new_height) // 2
		return image.crop((0, top, width, top + new_height))

def create_radial_mask(size):
	"""Create radial gradient mask with transparency at edges."""
	x = np.linspace(-1, 1, size[0])
	y = np.linspace(-1, 1, size[1])
	X, Y = np.meshgrid(x, y)
	dist = np.sqrt(X**2 + Y**2)
	mask = (1 - np.clip(dist, 0, 1)) * 255
	return Image.fromarray(mask.astype(np.uint8), "L")

def process_image(input_img, output_path, target_size):
	"""Process and save image with radial mask."""
	cropped = center_crop_to_ratio(input_img, target_size[0]/target_size[1])
	resized = cropped.resize(target_size, Image.LANCZOS)
	mask = create_radial_mask(target_size)
	
	rgba = resized.convert("RGBA")
	rgba.putalpha(mask)
	rgba.save(output_path)

# Core brush generation functionality
def generate_individual_brush(source_image_path, brush_id):
	"""Generate a single Procreate brush from source image."""
	print(f"Generating brush for {source_image_path} with ID {brush_id}")
	with TemporaryDirectory() as tmpdir:
		temp_dir = Path(tmpdir)
		
		# Process brush settings
		print(f"Processing brush settings for {brush_id}")
		process_brush_settings(temp_dir, brush_id)
		
		# Process grain image
		print(f"Processing grain image for {source_image_path}")
		grain_img = process_grain_image(source_image_path)
		grain_img.save(temp_dir/"Grain.png")
		
		# Create thumbnail
		print(f"Creating thumbnail for {brush_id}")
		(temp_dir/"QuickLook").mkdir(exist_ok=True)
		process_image(grain_img, temp_dir/"QuickLook/Thumbnail.png", (1060, 324))
		
		# Copy signature
		print(f"Copying signature for {brush_id}")
		copytree(template/"Signature", temp_dir/"Signature", dirs_exist_ok=True)
		
		# Package brush
		print(f"Packaging brush {brush_id}")
		create_brush_package(temp_dir, outdir/f"{brush_id}.brush")

def process_brush_settings(output_dir, brush_id):
	"""Generate and convert brush settings plist."""
	settings_file = output_dir/"Brush.archive"
	
	# Read and modify template
	with open(template/"Brush.archive") as f:
		content = f.read().replace("PLACEHOLDER_NAME", brush_id)
	
	with open(settings_file, "w") as f:
		f.write(content)
	
	# Convert to binary plist
	if os.name == "posix":
		executable = "plutil"
	elif os.name == "nt":
		executable = "bin.tmp/plutil.exe"

	run([executable, "-convert", "binary1", str(settings_file)], check=True)

def process_grain_image(img_path):
	"""Process grain image with inversion and alpha handling."""
	img = Image.open(img_path)
	
	return img.convert("L")

def create_brush_package(source_dir, output_path):
	"""Create final .brush package from directory contents."""
	if output_path.exists():
		output_path.unlink()
	make_archive(str(output_path), "zip", source_dir)

	# check if the zip is being used by another process, if so, wait
	
	for i in range(10):
		try:
			(Path(f"{output_path}.zip")).rename(output_path)
			break
		except:
			print(f"Waiting for {output_path} to be released")
			time.sleep(1)

def extract_brush_contents(brush_file, target_dir):
	"""Extract contents of a .brush file to target directory."""
	with zipfile.ZipFile(brush_file) as zf:
		zf.extractall(target_dir)

def create_brushset_package(source_dir, output_path):
	"""Package brush set directory into .brushset file."""
	if output_path.exists():
		output_path.unlink()
	make_archive(str(output_path), "zip", source_dir)
	Path(f"{output_path}.zip").rename(output_path)

def generate_brush_set(brush_ids: List[str], set_name: str):
	"""Generate a Procreate brush set with UUID-based folder structure."""
	print(f"Generating brush set {set_name} with brush IDs: {brush_ids}")
	with TemporaryDirectory() as tmpdir:
		temp_dir = Path(tmpdir)
		uuids = []
		
		# Process each brush and assign UUID
		for bid in brush_ids:
			brush_uuid = str(uuid.uuid4()).upper()
			uuids.append(brush_uuid)
			
			# Create UUID-named directory for this brush
			brush_dir = temp_dir / brush_uuid
			brush_dir.mkdir(exist_ok=True)
			
			# Extract source brush contents into UUID directory
			print(f"Extracting contents for brush {bid} into {brush_uuid}")
			with zipfile.ZipFile(outdir/f"{bid}.brush", 'r') as zf:
				zf.extractall(brush_dir)
		
		# Create brushset manifest
		print(f"Creating brushset manifest for {set_name}")
		create_brushset_manifest(temp_dir, uuids, set_name)
		
		# Package brush set
		print(f"Packaging brush set {set_name}")
		create_brushset_package(temp_dir, setdir/f"{set_name}.brushset")

def create_brushset_manifest(output_dir: Path, uuids: List[str], set_name: str):
	"""Generate brushset.plist with proper UUIDs."""
	print(f"Creating brushset.plist for {set_name} with UUIDs: {uuids}")
	plist = ET.Element("plist", version="1.0")
	root = ET.SubElement(plist, "dict")
	
	# Add brushes array
	ET.SubElement(root, "key").text = "brushes"
	array = ET.SubElement(root, "array")
	for uid in uuids:
		ET.SubElement(array, "string").text = uid
	
	# Add set name
	ET.SubElement(root, "key").text = "name"
	ET.SubElement(root, "string").text = set_name
	
	
	tree = ET.ElementTree(plist)
	manifest_path = output_dir / "brushset.plist"
	tree.write(manifest_path, encoding="UTF-8", xml_declaration=True)
	
	# Format with proper plist doctype
	with open(manifest_path, 'r+') as f:
		content = f.read()
		content = content.replace(
			'<plist version="1.0">',
			'''<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">'''
		)
		f.seek(0)
		f.write(content)
		f.truncate()
	print(f"brushset.plist created for {set_name}")


from concurrent.futures import ThreadPoolExecutor
def main(folder: Path, folder_name: str):
	"""Generate brushes and brush sets for all images in input directory."""
	# use threadpool to generate brushes in parallel

	executor = ThreadPoolExecutor(max_workers=4)
	executions = []

	print("Starting brush generation process")
	brush_ids = []
	
	to_do_dict = []
	# Generate individual brushes first
	for img_file in folder.iterdir():
		if img_file.is_file() and (match := re.match(r"(\d+)", img_file.stem)):
			brush_id = match.group(1)
			
			to_do_dict.append((brush_id, img_file))

	# sort by brush_id
	to_do_dict.sort(key=lambda x: int(x[0]))

	def action(bid=brush_id, img=img_file):
		generate_individual_brush(img, bid)
		brush_ids.append(bid)
		print(f"Generated brush: {bid}")

	

	for brush_id, img_file in to_do_dict:
		executions.append(executor.submit(action, brush_id, img_file))


	# Wait for all brush generation tasks to complete
	for execution in executions:
		try:
			execution.result()
		except Exception as e:
			traceback.print_exception(type(e), e, e.__traceback__)
	
	# Segment into sets of maximum 100 brushes
	if brush_ids:
		print(f"\nTotal brushes generated: {len(brush_ids)}")
		print("Creating brush sets...")

		# sort by brush_id
		brush_ids.sort(key=lambda x: int(x))
		
		# base_set_name = "MyTextureSet"
		# total_sets = (len(brush_ids) // 100) + (1 if len(brush_ids) % 100 else 0)
		
		# for i in range(total_sets):
		# 	set_name = f"{base_set_name} {i+1}"
		# 	start = i * 100
		# 	end = min((i + 1) * 100, len(brush_ids))
		# 	generate_brush_set(brush_ids[start:end], set_name)
		# 	print(f"Generated brush set: {set_name}")

		# print(f"\nTotal brush sets generated: {total_sets}")

		set_name = folder_name
		generate_brush_set(brush_ids, set_name)
	else:
		print("\nNo valid brushes found in input directory")
	
	print("\nBrush generation process completed")

if __name__ == "__main__":
	start = time.time()
	for folder in indir.iterdir():
		if folder.is_dir():
			folder_name = folder.name
			print(f"Processing folder {folder}")
			main(folder, folder_name)
		else:
			print(f"Skipping {folder}")
	print(f"Time taken: {time.time()-start:.2f} seconds")
	