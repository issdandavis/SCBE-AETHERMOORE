#!/usr/bin/env python3
"""Extract text from a .docx file using only stdlib (zipfile + xml).
Run: python C:\\Users\\issda\\SCBE-AETHERMOORE\\extract_docx.py
Output: C:\\Users\\issda\\SCBE-AETHERMOORE\\extracted_docx_content.txt
"""
import zipfile
import xml.etree.ElementTree as ET
import os
import sys

def extract_docx_text(docx_path):
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    with zipfile.ZipFile(docx_path) as z:
        xml_content = z.read('word/document.xml')
    
    tree = ET.fromstring(xml_content)
    paragraphs = tree.findall('.//w:p', ns)
    
    lines = []
    for p in paragraphs:
        texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
        line = ''.join(texts)
        lines.append(line)
    
    return '\n'.join(lines)

if __name__ == '__main__':
    docx_path = os.path.join(
        os.path.expanduser('~'), 'OneDrive', 'Documents',
        'Advanced CSIDE Writing Guide AI-Powered Interactive Fiction Development.docx'
    )
    output_path = os.path.join(
        os.path.expanduser('~'), 'SCBE-AETHERMOORE', 'extracted_docx_content.txt'
    )
    
    text = extract_docx_text(docx_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"Extracted {len(text)} characters to {output_path}")
