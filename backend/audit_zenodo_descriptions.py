import urllib.request
import json

rec_ids = ['8346860', '8253899', '13761290']
req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for rec_id in rec_ids:
    url = f"https://zenodo.org/api/records/{rec_id}"
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"==================================================")
        print(f"ZENODO RECORD {rec_id} DETAILED AUDIT")
        print(f"==================================================")
        print("Title:", data.get("metadata", {}).get("title"))
        print("Creators:", [c.get("name") for c in data.get("metadata", {}).get("creators", [])])
        print("Publication Date:", data.get("metadata", {}).get("publication_date"))
        print("DOI:", data.get("doi"))
        print("License:", data.get("metadata", {}).get("license"))
        print("Keywords:", data.get("metadata", {}).get("keywords"))
        print("Description:")
        print(data.get("metadata", {}).get("description"))
        print("\n")
