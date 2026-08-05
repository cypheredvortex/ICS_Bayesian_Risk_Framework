from pathlib import Path
from fastapi.testclient import TestClient
import backend.api as api

client = TestClient(api.app)
paths = [
    ('topology.csv', 'text/csv'),
    ('topology.xlsx', 'application/vnd.openxmlformats-officedocument-spreadsheetml.sheet'),
    ('topology.graphml', 'application/xml'),
    ('topology.xml', 'application/xml'),
    ('topology.aml', 'application/xml'),
]
base = Path(__file__).resolve().parent / 'validation_files'
for name, mime in paths:
    path = base / name
    with path.open('rb') as handle:
        response = client.post('/upload-topology-file', files={'file': (path.name, handle, mime)})
    print('UPLOAD', name, response.status_code)
    try:
        upload_data = response.json()
    except Exception:
        print(response.text[:2000])
        continue
    print(upload_data)
    if response.status_code != 200:
        print('---')
        continue
    analyze_response = client.post('/analyze', json={'topology': upload_data['topology'], 'evidence': []})
    print('ANALYZE', name, analyze_response.status_code)
    try:
        analyze_data = analyze_response.json()
    except Exception:
        print(analyze_response.text[:2000])
        print('---')
        continue
    print('graph nodes', len(analyze_data['graph']['nodes']), 'edges', len(analyze_data['graph']['edges']))
    print('risk scores', len(analyze_data['risk_scores']), 'attack paths', len(analyze_data['attack_paths']))
    print('summary', analyze_data['summary']['asset_count'], analyze_data['summary']['relationship_count'])
    print('---')
