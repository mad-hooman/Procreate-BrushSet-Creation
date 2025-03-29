import os
import csv
import zipfile
import tempfile
import plistlib

def get_brushset_name(brushset_path):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(brushset_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            plist_path = os.path.join(tmpdir, 'brushset.plist')
            if os.path.exists(plist_path):
                with open(plist_path, 'rb') as f:
                    plist_data = plistlib.load(f)
                    return plist_data.get('name', 'Name not found')
            return "brushset.plist missing"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    video_extensions = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'mpeg']
    output_csv = 'brushset_video_report.csv'
    video_folder = 'video.tmp'

    # Get all brushsets
    brushsets = []
    for file in os.listdir():
        if file.endswith('.brushset'):
            internal_name = get_brushset_name(file)
            brushsets.append({
                'filename': file,
                'internal_name': internal_name.strip() if isinstance(internal_name, str) else internal_name
            })

    # Get all videos from video.tmp folder
    video_map = {}
    if os.path.exists(video_folder) and os.path.isdir(video_folder):
        for file in os.listdir(video_folder):
            if '.' in file:
                name_part, ext_part = os.path.splitext(file)
                if ext_part[1:].lower() in video_extensions:
                    full_path = os.path.join(video_folder, file)
                    video_map.setdefault(name_part.strip(), []).append(full_path)
    else:
        print(f"Warning: Video folder '{video_folder}' not found")

    # Count name occurrences
    name_counts = {}
    for bs in brushsets:
        name = bs['internal_name']
        name_counts[name] = name_counts.get(name, 0) + 1

    # Generate main report
    report_data = []
    for bs in brushsets:
        internal_name = bs['internal_name']
        videos = video_map.get(internal_name, [])
        
        notes = []
        if name_counts[internal_name] > 1:
            notes.append(f"Duplicate name ({name_counts[internal_name]}x)")
        if len(videos) > 1:
            notes.append(f"Multiple videos: {len(videos)}")
        
        report_data.append({
            'Brushset File': bs['filename'],
            'Internal Name': internal_name,
            'Video Path(s)': '; '.join(videos) if videos else 'MISSING',
            'Notes': ' | '.join(notes)
        })

    # Prepare footer with missing and duplicates
    footer_rows = [
        {'Brushset File': '--- MISSING ENTRIES ---', 'Internal Name': '', 'Video Path(s)': '', 'Notes': ''},
        *[row for row in report_data if row['Video Path(s)'] == 'MISSING'],
        {'Brushset File': '--- DUPLICATE ENTRIES ---', 'Internal Name': '', 'Video Path(s)': '', 'Notes': ''},
        *[row for row in report_data if 'Duplicate' in row['Notes']]
    ]

    # Write CSV with footer
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Brushset File', 'Internal Name', 'Video Path(s)', 'Notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write main data
        writer.writeheader()
        writer.writerows(report_data)
        
        # Write footer
        writer.writerows(footer_rows)

    print(f"Report generated: {output_csv}")
    print(f"Found {len(video_map)} video base names in {video_folder}")

if __name__ == '__main__':
    main()