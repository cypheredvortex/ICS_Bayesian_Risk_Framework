import zipfile
from pathlib import Path
import vsdx

file = Path('tmp_vsdx_test.vsdx')
if file.exists():
    file.unlink()
with zipfile.ZipFile(file, 'w') as z:
    z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.document.main+xml"/>
<Override PartName="/visio/_rels/document.xml.rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>
<Override PartName="/visio/pages/_rels/pages.xml.rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>
</Types>''')
    z.writestr('docProps/app.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<HeadingPairs><vt:vector size="2"><vt:variant><vt:lpstr>Pages</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>
<TitlesOfParts><vt:vector size="1"><vt:lpstr>Page-1</vt:lpstr></vt:vector></TitlesOfParts>
</Properties>''')
    z.writestr('visio/document.xml', '<?xml version="1.0" encoding="UTF-8"?><Document></Document>')
    z.writestr('visio/_rels/document.xml.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>')
    z.writestr('visio/pages/pages.xml', '<?xml version="1.0" encoding="UTF-8"?><Pages xmlns="http://schemas.microsoft.com/office/visio/2012/main"><Page ID="1" Name="Page-1" NameU="Page-1"><Rel r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></Page></Pages>')
    z.writestr('visio/pages/_rels/pages.xml.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="page1.xml" Type="http://schemas.microsoft.com/visio/2010/relationships/page"/></Relationships>')
    z.writestr('visio/pages/page1.xml', '<?xml version="1.0" encoding="UTF-8"?><PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main"><Shapes><Shape ID="1"><Text>asset,A,device</Text></Shape><Shape ID="2"><Text>relationship,A,B,connects-to,false,modbus,low</Text></Shape></Shapes></PageContents>')
print('created', file.exists())
doc = vsdx.VisioFile(str(file))
print('opened', len(doc.pages), doc.get_page_names())
for p in doc.pages:
    print('page child count', len(p.child_shapes))
    for s in p.child_shapes:
        print('shape', getattr(s, 'text', None))
