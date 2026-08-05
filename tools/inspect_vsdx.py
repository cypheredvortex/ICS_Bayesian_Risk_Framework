from zipfile import ZipFile
from pathlib import Path
p = Path('tests/validation_files/topology.vsdx')
if not p.exists():
    print('MISSING', p)
    raise SystemExit(1)

with ZipFile(p) as z:
    xmls = [n for n in z.namelist() if n.lower().endswith('.xml')]
    print('XML_COUNT', len(xmls))
    for n in xmls:
        data = z.read(n)
        try:
            txt = data.decode('utf-8', errors='ignore').lower()
        except Exception:
            continue
        if any(tok in txt for tok in ('asset', 'relationship', 'shape', 'text', 't')):
            print('---', n)
            idx = 0
            for tok in ('asset', 'relationship', 'shape', 'text'):
                i = txt.find(tok)
                if i != -1:
                    print('FOUND', tok, 'at', i)
                    start = max(0, i-200)
                    print(txt[start:i+200])
                    break
            # stop after first match to keep output small
            break
    else:
        print('NO_MARKERS_FOUND')
