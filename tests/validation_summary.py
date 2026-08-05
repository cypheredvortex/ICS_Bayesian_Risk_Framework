import json
from pathlib import Path

path = Path('tests/validation_report.json')
if not path.exists():
    raise SystemExit('missing report file')

data = json.loads(path.read_text(encoding='utf-8'))
summary = {}
for fmt, info in data.get('uploads', {}).items():
    summary[fmt] = {
        'upload_status': info.get('status_code'),
        'analysis_status': data.get('analyses', {}).get(fmt, {}).get('status_code') if info.get('status_code') == 200 else None,
        'uploaded_assets': info.get('response', {}).get('asset_count') if isinstance(info.get('response'), dict) else None,
        'uploaded_rels': info.get('response', {}).get('relationship_count') if isinstance(info.get('response'), dict) else None,
    }

print(json.dumps(summary, indent=2))
print('\nFormats with failures:')
for fmt, info in summary.items():
    if info['upload_status'] != 200 or (info['analysis_status'] is not None and info['analysis_status'] != 200):
        print(fmt, info)
