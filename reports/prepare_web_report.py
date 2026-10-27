"""Create an edited Word copy and a self-contained HTML article from the report."""
from pathlib import Path
from copy import deepcopy
import base64
import html
import re
import zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W = '{' + NS['w'] + '}'

EDITS = {
0: 'Medicaid and CHIP: Fewer Enrollees, Continued Spending Pressure',
1: 'What the four states show',
2: 'Fewer people enrolled does not always mean lower spending. Across New York, Illinois, Washington, and Pennsylvania, Medicaid and CHIP enrollment fell after pandemic-era coverage protections ended. Yet spending per average enrollee rose in all four states in FY2024. This report looks at that gap and what the forecasts suggest for the years ahead.',
3: 'The analysis combines monthly enrollment from June 2017 through March 2026 with annual spending from federal fiscal years FY1997–FY2024. Spending includes federal and nonfederal funding. All figures combine Medicaid and CHIP. Spending per average enrollee means annual spending divided by average monthly enrollment in the same fiscal year; comparisons start in FY2018, the first full year of enrollment data.',
4: 'Enrollment forecasts run through March 2036. The model allows trends to change around the pandemic and the return of eligibility reviews, while accounting for seasonal patterns [1]. Spending forecasts run through FY2034. The Holt model extends the longer-term trend but gradually slows its growth. A second model, used for Illinois, Washington, and Pennsylvania, allows the spending trend to change at selected dates. These are projections based on past patterns, not estimates of what policy changes caused.',
5: 'New York: Enrollment falls, but spending keeps rising',
6: 'New York shows why enrollment alone cannot explain a Medicaid budget. Monthly enrollment peaked at 7.63 million in June 2023 and fell to 6.45 million by March 2026. In FY2024, spending rose 3.4% to $97.33 billion while average monthly enrollment fell 7.0%. Spending per average enrollee therefore increased 11.3% to $13,989.',
7: 'Higher payment rates may help explain the gap. New York’s FY2024 budget included a 7.5% increase in hospital inpatient reimbursement. The state also adjusted personal care and Consumer Directed Personal Assistance Program payments to reflect minimum wage increases [2,3]. Changes like these can push costs up even when fewer people are enrolled.',
8: 'The forecasts point in the same direction: enrollment falls to 5.03 million in March 2036, while the Holt model puts spending at $117.00 billion in FY2034. Lower enrollment may leave the state facing continued budget pressure.',
19: 'Illinois: The needs of remaining enrollees matter',
20: 'In Illinois, who stays enrolled matters as much as how many people leave. The state’s FY2024 annual report identifies greater medical needs among remaining enrollees as one reason liabilities rose after eligibility reviews resumed [4]. A smaller covered population can still require costly care.',
21: 'Monthly enrollment fell from 3.87 million in July 2023 to 3.01 million in March 2026. In FY2024, average enrollment dropped 8.6%, but spending rose 1.1% to $33.28 billion. Spending per average enrollee increased 10.6% to $9,532. Hospital rate increases may also have added pressure; the state’s January 2024 notice said the fee-for-service changes were awaiting federal approval [5].',
22: 'Between FY2018 and FY2024, spending per average enrollee rose 31.6%, from $7,241 to $9,532. Both spending forecasts reach about $41 billion in FY2034: $41.39 billion under Holt and $41.14 billion under the model with trend changes.',
23: 'The enrollment forecast needs more caution. It falls to 0.80 million by March 2036 because the model carries the final fitted decline forward for ten years. That could stretch a temporary renewal-related drop too far into the future. This projection should be checked against newer enrollment data before it is used for planning.',
37: 'Washington: The largest jump in spending per enrollee',
38: 'Washington had the largest FY2024 increase in spending per average enrollee among the four states. Spending rose 9.0% to $20.24 billion while average enrollment fell 11.5%, pushing the ratio up 23.2% to $10,748. From FY2018 to FY2024, it rose 55.0%, from $6,934—the largest percentage increase in the group.',
39: 'Enrollment patterns can also differ by age. Washington extended continuous eligibility for eligible children in free Apple Health through the month of their sixth birthday [6]. That helps protect coverage for young children, but overall enrollment still fell from 2.20 million in May 2023 to 1.79 million in March 2026.',
40: 'The enrollment forecast then stays fairly flat, reaching 1.82 million in March 2036. Both spending models rise, reaching $24.27 billion under Holt and $28.00 billion under the model with trend changes in FY2034. With enrollment relatively stable, the next question is what is driving costs within the covered population. More detail on services, payments, and eligibility groups would help answer it.',
54: 'Pennsylvania: The spending outlook depends on the model',
55: 'Pennsylvania’s enrollment peaked at 3.74 million in April 2023 and fell to 3.01 million by March 2026. The return of eligibility reviews offers a possible explanation: some people no longer qualified or did not complete renewal [7]. The model projects a slower decline to 2.51 million by March 2036, about 17% below the latest observed level.',
56: 'Spending fell about 1.0% to $44.05 billion in FY2024, while average monthly enrollment dropped 11.2%. Because enrollment fell much faster than spending, spending per average enrollee still rose 11.5% to $13,509. That was 34.3% above its FY2018 level of $10,062.',
57: 'The spending forecasts tell different stories. Holt follows the longer-term upward pattern, reaching $51.60 billion in FY2034—about 17% above FY2024. The model with trend changes extends the recent downward pattern, reaching $28.24 billion—about 36% below FY2024. The gap shows how strongly the outlook depends on which historical trend continues.',
58: 'Pennsylvania therefore has a clearer enrollment story than spending story. Enrollment is projected to fall, but the direction of total spending remains uncertain. Neither model can establish whether the recent spending decrease will last.',
72: 'Figures and forecasts come from the project’s cleaned data and state result tables. The original report records the government sources below as checked on October 20, 2026. Policy examples suggest possible explanations; the analysis does not establish cause and effect. State budget periods and program definitions may differ from those used here.',
}

def text(p):
    return ''.join(p.xpath('.//w:t/text()', namespaces=NS))

def replace(p, value):
    props = p.find('w:pPr', NS)
    runprops = p.find('w:r/w:rPr', NS)
    for child in list(p):
        if child is not props:
            p.remove(child)
    run = E.SubElement(p, W + 'r')
    if runprops is not None:
        run.append(deepcopy(runprops))
    E.SubElement(run, W + 't').text = value

def main():
    with zipfile.ZipFile(ROOT / 'State_Result_Figures.docx') as source:
        root = E.fromstring(source.read('word/document.xml'))
        body = root.find('w:body', NS)
        paragraphs = body.findall('w:p', NS)
        for index, value in EDITS.items():
            replace(paragraphs[index], value)
        for p in paragraphs:
            if text(p).lower().startswith('source: project data and model output'):
                body.remove(p)
        # Place a short synthesis before the references.
        for value, heading in [
            ('What this means for planning', True),
            ('Across all four states, fewer enrollees have not translated into an equal drop in spending. Spending per average enrollee rose in FY2024 even in Pennsylvania, where total spending fell slightly. Payment rates and the care needs of remaining enrollees are possible reasons, but the data here cannot separate their effects.', False),
            ('The forecasts are useful starting points for planning. Illinois’s steep enrollment decline and Pennsylvania’s widely different spending forecasts show why long-range results need care. Updating the models as new data arrive will help show which trends are lasting.', False),
            ('A brief note on the models', True),
            ('The enrollment model includes trend changes in March 2020, April 2023, and July 2024, plus recurring monthly patterns. July 2024 is a modeling choice to capture a possible slowdown in enrollment losses, rather than a shared policy event. The alternative spending model uses FY2020, FY2023, and FY2024 as trend-change points. Both approaches extend historical patterns and may miss future policy or economic changes.', False),
        ]:
            p = deepcopy(paragraphs[1] if heading else paragraphs[2])
            replace(p, value)
            body.insert(body.index(paragraphs[71]), p)
        out = ROOT / 'reports'
        out.mkdir(exist_ok=True)
        with zipfile.ZipFile(out / 'State_Result_Figures_Web_Edited.docx', 'w', zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                target.writestr(deepcopy(item), E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True) if item.filename == 'word/document.xml' else source.read(item.filename))

        rels = {r.get('Id'): r.get('Target') for r in E.fromstring(source.read('word/_rels/document.xml.rels'))}
        parts = []
        caption = None
        section = ''
        headings = {EDITS[i] for i in (1, 5, 19, 37, 54)} | {'What this means for planning', 'A brief note on the models', 'References'}
        for p in body.findall('w:p', NS):
            value = text(p)
            if value.startswith('Figure '):
                caption = value
                continue
            for blip in p.xpath('.//a:blip', namespaces=NS):
                path = 'word/' + rels[blip.get('{' + NS['r'] + '}embed')]
                image = base64.b64encode(source.read(path)).decode()
                label = caption or 'Report chart'
                parts.append(f'<figure><img src="data:image/png;base64,{image}" alt="{html.escape(section + ": " + label)}" loading="lazy"><figcaption>{html.escape(label)}</figcaption></figure>')
                caption = None
            if not value:
                continue
            if value == EDITS[0]:
                parts.append(f'<h1>{html.escape(value)}</h1>')
            elif value in headings:
                section = value
                parts.append(f'<h2>{html.escape(value)}</h2>')
            else:
                content = ''
                for child in p:
                    chunk = html.escape(text(child))
                    if child.tag == W + 'hyperlink':
                        url = rels.get(child.get('{' + NS['r'] + '}id'), '')
                        chunk = f'<a href="{html.escape(url, quote=True)}">{chunk}</a>'
                    content += chunk
                parts.append(f'<p>{content}</p>')
        page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Medicaid and CHIP: Fewer Enrollees, Continued Spending Pressure</title>
<style>
body{margin:0;background:#fff;color:#24303c;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.75}
main{max-width:900px;margin:auto;padding:40px 24px 72px}h1,h2{line-height:1.25;color:#163d54}h1{font-size:clamp(2rem,5vw,3rem);margin:0 0 32px}h2{font-size:1.55rem;margin:48px 0 18px}p{margin:0 0 20px}figure{margin:32px 0}img{display:block;width:100%;height:auto}figcaption{font-size:.9rem;color:#52616c;margin-top:10px}a{color:#155a85;overflow-wrap:anywhere}
@media print{main{padding:0}figure{break-inside:avoid}h2{break-after:avoid}}
</style></head><body><main><article>
''' + '\n'.join(parts) + '\n</article></main></body></html>\n'
        (out / 'medicaid-state-trends.html').write_text(page, encoding='utf-8')
        assert page.count('<figure>') == 15
        assert page.count('<a href=') == 7
        assert 'Source: Project data and model output' not in page
        assert len(root.xpath('//a:blip', namespaces=NS)) == 15
        print('Created edited Word and self-contained HTML: 15 charts, 7 source links; repeated source captions removed.')

if __name__ == '__main__':
    main()
