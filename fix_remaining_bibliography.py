#!/usr/bin/env python3
"""
Fix remaining truncated bibliography entries
Uses chapter title number to correctly map to XHTML files
"""

import os
import re
import html
from pathlib import Path

OUTPUT_DIR = "/workspace/xml_fully_fixed/9781071643624"
XHTML_DIR = "/workspace/xhtml_source/html"

def extract_citations_from_xhtml(xhtml_path):
    """Extract full citations from XHTML file."""
    citations = {}
    
    try:
        with open(xhtml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract citations
        citation_pattern = r'<div class="CitationContent" id="(CR\d+)">(.*?)</div>'
        matches = re.findall(citation_pattern, content, re.DOTALL)
        
        for cit_id, cit_content in matches:
            # Clean HTML tags but preserve meaningful content
            clean_content = re.sub(r'<span class="RefSource">[^<]*</span>', '', cit_content)
            clean_content = re.sub(r'<span class="Occurrence[^"]*">[^<]*</span>', '', clean_content)
            clean_content = re.sub(r'<a[^>]*>([^<]*)</a>', r'\1', clean_content)
            clean_content = re.sub(r'<em[^>]*>([^<]*)</em>', r'\1', clean_content)
            clean_content = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', clean_content)
            clean_content = re.sub(r'</?[a-z][^>]*>', '', clean_content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            clean_content = html.unescape(clean_content)
            
            # Extract citation number
            cit_num_match = re.search(r'CR(\d+)', cit_id)
            if cit_num_match:
                cit_num = int(cit_num_match.group(1))
                citations[cit_num] = clean_content
                
        return citations
    except Exception as e:
        print(f"Error parsing {xhtml_path}: {e}")
        return {}


def fix_bibliography_file(xml_path, citations):
    """Fix truncated bibliography entries in XML file."""
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fixes_made = 0
    
    # Find all bibliomixed entries
    bibliomixed_pattern = r'<bibliomixed id="([^"]+)">([^<]*)</bibliomixed>'
    matches = list(re.finditer(bibliomixed_pattern, content))
    
    for match in matches:
        bib_id = match.group(1)
        current_content = match.group(2)
        
        # Extract the bib number
        bib_num_match = re.search(r'bib(\d+)$', bib_id)
        if not bib_num_match:
            continue
        
        bib_num = int(bib_num_match.group(1))
        
        # Check if this citation exists and is longer
        if bib_num in citations:
            full_citation = citations[bib_num]
            
            # Only fix if current content is significantly shorter
            if len(current_content.strip()) < len(full_citation) * 0.7:
                old_entry = match.group(0)
                new_entry = f'<bibliomixed id="{bib_id}">{html.escape(full_citation)}</bibliomixed>'
                content = content.replace(old_entry, new_entry, 1)
                fixes_made += 1
    
    if fixes_made > 0:
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return fixes_made


def get_xhtml_file_for_chapter(title_chapter_num):
    """Get XHTML file for a given chapter number from title."""
    xhtml_files = list(Path(XHTML_DIR).glob(f'*_{title_chapter_num}_Chapter.xhtml'))
    if xhtml_files:
        return xhtml_files[0]
    return None


def main():
    print("Fixing Remaining Bibliography Entries")
    print("=" * 60)
    
    # Find all bibliography files
    bib_files = []
    for f in sorted(Path(OUTPUT_DIR).glob('*.xml')):
        try:
            content = open(f).read()
            if '<bibliography' in content or '<bibliomixed' in content:
                bib_files.append(f)
        except:
            pass
    
    print(f"Found {len(bib_files)} bibliography files")
    
    total_fixes = 0
    
    for bib_file in bib_files:
        content = open(bib_file).read()
        
        # Get chapter title number
        title_match = re.search(r'<chaptertitle>(\d+)\.', content)
        if not title_match:
            print(f"  WARNING: Could not extract chapter number from {bib_file.name}")
            continue
        
        title_ch_num = int(title_match.group(1))
        
        # Get corresponding XHTML file
        xhtml_file = get_xhtml_file_for_chapter(title_ch_num)
        if not xhtml_file:
            print(f"  WARNING: No XHTML file for Chapter {title_ch_num}")
            continue
        
        # Extract citations from XHTML
        citations = extract_citations_from_xhtml(xhtml_file)
        if not citations:
            continue
        
        # Fix bibliography entries
        fixes = fix_bibliography_file(bib_file, citations)
        
        if fixes > 0:
            print(f"  {bib_file.name}: Fixed {fixes} entries (Chapter {title_ch_num})")
            total_fixes += fixes
    
    print(f"\n{'=' * 60}")
    print(f"Total additional fixes: {total_fixes}")


if __name__ == "__main__":
    main()
