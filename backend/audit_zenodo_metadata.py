import urllib.request
import json

records = {
    'Part I': '8346860',
    'Part II': '8253899',
    'Part III': '13761290'
}

req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for part, rec_id in records.items():
    url = f'https://zenodo.org/api/records/{rec_id}'
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f'=== {part} (Record {rec_id}) ===')
            print('Title:', data.get('metadata', {}).get('title'))
            print('Publication Date:', data.get('metadata', {}).get('publication_date'))
            print('DOI:', data.get('doi'))
            print('Description:', data.get('metadata', {}).get('description', '')[:300] + '...')
            print('Files:')
            for f in data.get('files', []):
                fname = f.get('key') or f.get('filename')
                fsize = f.get('size') or f.get('file_size')
                fchk = f.get('checksum') or f.get('md5')
                flink = f.get('links', {}).get('self') or f.get('links', {}).get('content')
                print(f'  - Name: {fname}')
                print(f'    Size: {fsize} bytes ({fsize/(1024**3):.2f} GB)')
                print(f'    Checksum: {fchk}')
                print(f'    Download Link: {flink}')
    except Exception as e:
        print(f'Error fetching {part}: {e}')
