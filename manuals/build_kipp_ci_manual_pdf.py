"""Render the student Markdown manual to a shareable, bookmarked PDF.

Run with Python that has reportlab: python manuals/build_kipp_ci_manual_pdf.py
"""
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import Font
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, Preformatted, HRFlowable,
)

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'manuals/kipp-ci-panduan-mahasiswa.md'
OUTPUT=ROOT/'output/pdf/kipp-ci-panduan-mahasiswa.pdf'
FONT_ROOTS=[Path('/usr/share/fonts/truetype/dejavu'),
    Path('/home/armein/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/share/fonts/truetype')]
fontroot=next((p for p in FONT_ROOTS if (p/'DejaVuSans.ttf').exists()),None)
for name,file in [('Body','DejaVuSans.ttf'),('BodyBold','DejaVuSans-Bold.ttf'),('Mono','DejaVuSansMono.ttf')]:
    if fontroot:
        pdfmetrics.registerFont(TTFont(name,str(fontroot/file)))
    else:
        base={'Body':'Helvetica','BodyBold':'Helvetica-Bold','Mono':'Courier'}[name]
        pdfmetrics.registerFont(Font(name,base,'WinAnsiEncoding'))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
NAVY=colors.HexColor('#14364D'); TEAL=colors.HexColor('#087E8B'); GRAY=colors.HexColor('#526572')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ManualTitle',fontName='BodyBold',fontSize=26,leading=33,textColor=NAVY,spaceAfter=16))
styles.add(ParagraphStyle(name='ManualH2',fontName='BodyBold',fontSize=16,leading=21,textColor=NAVY,spaceBefore=18,spaceAfter=10,keepWithNext=True))
styles.add(ParagraphStyle(name='ManualH3',fontName='BodyBold',fontSize=11.5,leading=16,textColor=TEAL,spaceBefore=12,spaceAfter=6,keepWithNext=True))
styles.add(ParagraphStyle(name='ManualBody',fontName='Body',fontSize=10,leading=15,spaceAfter=7))
styles.add(ParagraphStyle(name='ManualCell',fontName='Body',fontSize=8.5,leading=12,spaceAfter=0,splitLongWords=True))
styles.add(ParagraphStyle(name='ManualTH',fontName='BodyBold',fontSize=8.5,leading=12,textColor=colors.white,spaceAfter=0))
styles.add(ParagraphStyle(name='ManualQuote',fontName='Body',fontSize=10,leading=15,leftIndent=12,rightIndent=10,spaceBefore=4,spaceAfter=10,textColor=NAVY,borderColor=TEAL,borderWidth=.6,borderPadding=8))
styles.add(ParagraphStyle(name='ManualCode',fontName='Mono',fontSize=8.4,leading=12,leftIndent=10,rightIndent=6,spaceBefore=4,spaceAfter=9,backColor=colors.HexColor('#F0F5F7'),borderPadding=8))
styles.add(ParagraphStyle(name='ManualList',parent=styles['ManualBody'],leftIndent=13,firstLineIndent=-10,spaceAfter=5))


def normalize(text):
    return text.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')


def inline(text):
    text=escape(normalize(text))
    text=re.sub(r'`([^`]+)`',lambda m:'<font name="Mono">'+m[1]+'</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<link href="\2" color="#087E8B">\1</link>',text)
    return text


class ManualDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name=='ManualH2':
            plain=flowable.getPlainText()
            match=re.match(r'(\d+)\.',plain)
            if match:
                key='section'+match[1]
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(plain,key,level=0,closed=False)


def footer(canvas,doc):
    width,height=A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#CBD7DC')); canvas.setLineWidth(.5)
    canvas.line(doc.leftMargin,31,width-doc.rightMargin,31)
    canvas.setFont('Body',7.5);canvas.setFillColor(GRAY)
    canvas.drawString(doc.leftMargin,19,'KIPP_ci_bot | Panduan mahasiswa | 10 November 2026')
    canvas.drawRightString(width-doc.rightMargin,19,f'{doc.page}')
    if doc.page>1:
        canvas.setFont('Body',8)
        canvas.drawString(doc.leftMargin,height-25,'KIPP-CI v3 - TISE Collective Intelligence Laboratory')
    canvas.restoreState()


def build():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    lines=SOURCE.read_text(encoding='utf-8').splitlines()
    story=[];i=0;toc=False
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            i+=1;continue
        if line.startswith('# '):
            story.append(Paragraph(inline(line[2:]),styles['ManualTitle']))
            story.append(HRFlowable(width='100%',thickness=2,color=TEAL,spaceAfter=12))
            i+=1;continue
        if line.startswith('## '):
            title=line[3:]
            if title=='Daftar isi':
                story.append(PageBreak());toc=True
            elif title.startswith('1. '):
                story.append(PageBreak());toc=False
            story.append(Paragraph(inline(title),styles['ManualH2']))
            i+=1;continue
        if line.startswith('### '):
            story.append(Paragraph(inline(line[4:]),styles['ManualH3']));i+=1;continue
        if line.startswith('```'):
            block=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]);i+=1
            # Paragraph wrapping keeps long commands inside the page width.
            for code in block:
                story.append(Paragraph(escape(normalize(code)),styles['ManualCode']))
            i+=1;continue
        if line.startswith('|'):
            table=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',cell.replace(' ','')) for cell in cells):
                    table.append(cells)
                i+=1
            count=len(table[0]);available=A4[0]-88
            if count==2: widths=[146,available-146]
            elif count==3 and table[0][0]=='Perintah': widths=[174,100,available-274]
            elif count==3 and table[0][0]=='Awalan': widths=[52,130,available-182]
            else: widths=[available/count]*count
            data=[[Paragraph(inline(cell),styles['ManualTH' if r==0 else 'ManualCell']) for cell in row] for r,row in enumerate(table)]
            t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F7F9')]),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                ('LINEBELOW',(0,0),(-1,0),.5,NAVY),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#DCE4E8'))]))
            story.extend([t,Spacer(1,9)]);continue
        if line=='---':
            story.append(HRFlowable(width='100%',thickness=.5,color=GRAY,spaceBefore=10,spaceAfter=10));i+=1;continue
        if line.startswith('> '):
            story.append(Paragraph(inline(line[2:]),styles['ManualQuote']));i+=1;continue
        match=re.match(r'(\d+)\. (.*)',line)
        if match:
            text=inline(match[2])
            if toc: text=f'<link href="#section{match[1]}" color="#087E8B">{text}</link>'
            story.append(Paragraph(f'{match[1]}. {text}',styles['ManualList']));i+=1;continue
        if line.startswith('- '):
            text=line[2:]
            bullet='[ ]' if text.startswith('[ ]') else '-'
            if bullet=='[ ]': text=text[3:].strip()
            story.append(Paragraph(escape(bullet)+' '+inline(text),styles['ManualList']));i+=1;continue
        chunks=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|>|- |\d+\.)',lines[i].strip()):
            chunks.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(' '.join(chunks)),styles['ManualBody']))
    doc=ManualDoc(str(OUTPUT),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=45,bottomMargin=45,
                  title='Panduan Mahasiswa KIPP_ci_bot',author='II2100 KIPP',subject='Petunjuk penggunaan KIPP-CI v3 untuk mahasiswa')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUTPUT)


if __name__=='__main__':
    build()
