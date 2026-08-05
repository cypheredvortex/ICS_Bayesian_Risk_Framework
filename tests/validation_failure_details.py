import json
from pathlib import Path

path = Path('tests/validation_report.json')
if not path.exists():
    raise SystemExit('missing validation_report.json')

data = json.loads(path.read_text(encoding='utf-8'))
for fmt in ['csv', 'xlsx', 'xml', 'vsdx', 'vsd']:
    info = data['uploads'].get(fmt)
    print('---', fmt, '---')
    if info is None:
        print('missing info')
        continue
    print('status:', info.get('status_code'))
    resp = info.get('response')
    if isinstance(resp, dict):
        print(json.dumps(resp, indent=2))
    else:
        print(resp)
