"""Sync the HTML article from the saved Word document without editorial changes."""
from pathlib import Path
import base64
import html
import posixpath
import zipfile
from lxml import etree as E
from lxml import html as H

HERE = Path(__file__).resolve().parent
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W = '{' + NS['w'] + '}'

def text(node):
    return ''.join(node.xpath('.//w:t/text()', namespaces=NS))

def main():
    target = HERE / 'medicaid-state-trends.html'
    previous = H.fromstring(target.read_text())
    css = previous.find('.//style').text
    parts, expected = [], []
    heading_texts = {'What the four states show', 'What this means for planning',
                     'A brief note on the models', 'References'}
    with zipfile.ZipFile(HERE / 'State_Result_Figures_Web_Edited.docx') as archive:
        doc = E.fromstring(archive.read('word/document.xml'))
        rels = {r.get('Id'): r.get('Target') for r in E.fromstring(archive.read('word/_rels/document.xml.rels'))}
        paragraphs = doc.findall('w:body/w:p', NS)
        title = next(text(p) for p in paragraphs if text(p).strip())
        section, figure, count = '', '', 0
        for p in paragraphs:
            value = text(p)
            if value:
                expected.append(value)
                content = ''
                for child in p:
                    chunk = html.escape(text(child))
                    if child.tag == W + 'hyperlink':
                        url = rels.get(child.get('{' + NS['r'] + '}id'), '')
                        chunk = f'<a href="{html.escape(url, quote=True)}">{chunk}</a>'
                    content += chunk
                if value == title:
                    parts.append(f'<h1>{content}</h1>')
                elif value in heading_texts or any(value.startswith(s + ':') for s in ('New York', 'Illinois', 'Washington', 'Pennsylvania')):
                    section = value
                    parts.append(f'<h2>{content}</h2>')
                elif value.startswith('Figure '):
                    figure = value
                    parts.append(f'<p class="chart-title">{content}</p>')
                else:
                    parts.append(f'<p>{content}</p>')
            for blip in p.xpath('.//a:blip', namespaces=NS):
                path = posixpath.normpath('word/' + rels[blip.get('{' + NS['r'] + '}embed')])
                encoded = base64.b64encode(archive.read(path)).decode()
                ext = path.rsplit('.', 1)[-1].lower()
                mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}.get(ext, 'image/' + ext)
                label = html.escape(section + ': ' + (figure or 'Chart'), quote=True)
                parts.append(f'<figure><img src="data:{mime};base64,{encoded}" alt="{label}" loading="lazy"></figure>')
                count += 1
        page = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                f'<title>{html.escape(title)}</title><style>{css}\n.chart-title{{font-weight:600;margin:32px 0 8px}}.chart-title+figure{{margin-top:8px}}</style>'
                '</head><body><main><article>\n' + '\n'.join(parts) + '\n</article></main></body></html>\n')
        parsed = H.fromstring(page)
        actual = [''.join(p.itertext()) for p in parsed.xpath('//article/*') if p.tag != 'figure']
        assert actual == expected, 'HTML text differs from Word'
        assert len(parsed.xpath('//img')) == len(doc.xpath('//a:blip', namespaces=NS))
        word_links = [rels[h.get('{' + NS['r'] + '}id')] for h in doc.xpath('//w:hyperlink[@r:id]', namespaces=NS)]
        assert parsed.xpath('//article//a/@href') == word_links
        target.write_text(page, encoding='utf-8')
        print(f'Synced {len(expected)} text blocks, {count} images, {len(word_links)} hyperlinks. Text and link order match Word exactly.')

if __name__ == '__main__':
    main()
