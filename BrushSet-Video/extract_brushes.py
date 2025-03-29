"""
extract a file.brushset as zip, open the zip/brushset.plist
the content there:
```
<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>brushes</key><array><string>F570A7D8-315F-4FB0-9969-D5F67952BE34</string><string>B8668DB4-E13C-441B-9C6D-2F43A9F182A9</string><string>FE5C4D59-091E-47D3-ADB7-8A12937B7315</string>
.....
</array><key>name</key><string>Brick Wall</string></dict></plist>
```

i need the name of the brushset and the uuid of each brush
the uuid of each brush is the string in the array
return the name and the list of uuids (there are folders with the same name as UUID inside the zip, return their path as well)
"""

from pathlib import Path
import zipfile
import plistlib

def extract_brushset_info(brushset_file: str, temp_dir: str):
	"""
	Extracts the name and UUIDs of brushes from a .brushset file.
	
	Args:
		brushset_file (str): Path to the .brushset file.
		temp_dir (str): Path to the temporary directory where the file will be extracted.
	
	Returns:
		dict: A dictionary with 'name' (str) and 'brushes' (list of dicts with 'uuid' and 'path').
	"""
	temp_path = Path(temp_dir)
	temp_path.mkdir(parents=True, exist_ok=True)
	
	with zipfile.ZipFile(brushset_file, 'r') as zip_ref:
		zip_ref.extractall(temp_path)
	
	plist_path = temp_path / 'brushset.plist'
	if not plist_path.exists():
		raise FileNotFoundError("brushset.plist not found inside the extracted brushset.")
	
	with plist_path.open('rb') as plist_file:
		plist_data = plistlib.load(plist_file)
	
	brushset_name = plist_data.get('name', 'Unknown')
	brush_uuids = plist_data.get('brushes', [])

	def thumbnail(path: Path):
		return path/"QuickLook"/"thumbnail.png"
	
	brushes = [
		{"uuid": uuid, 
		"brush_path": str(temp_path / uuid),
		"thumbnail": str(thumbnail(temp_path / uuid)),
		"path": str(thumbnail(temp_path / uuid))}
		for uuid in brush_uuids
	]
	
	return {"name": brushset_name, "brushes": brushes}

if __name__ == "__main__":
	# Example usage
	brushset_file = "Assets/Brick Wall.tmp.brushset"
	temp_dir = "Temp.tmp"
	
	result = extract_brushset_info(brushset_file, temp_dir)
	print(result)
