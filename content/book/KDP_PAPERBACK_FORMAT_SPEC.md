# KDP Paperback Format Specifications

## Saved from KDP help docs 2026-03-22
## Use this when building the paperback edition

### File Format
- **Preferred**: PDF (PDF/X-1a format)
- **Also accepted**: DOC, DOCX, RTF, HTML, TXT (auto-converted to PDF)
- **Max file size**: 650 MB
- **No bleed needed** for text-only books (no images to page edge)

### Page Setup
- **Trim size**: 5.5 x 8.5 in (our HOUSE_STYLE.md setting) or 6 x 9 in
- **Single pages only** — no spreads
- **All pages same orientation**
- **Even page count** (KDP rounds up if odd)
- **Min pages**: depends on trim/ink/paper selection
- **Pagination**: even numbers LEFT, odd numbers RIGHT

### Margins (from HOUSE_STYLE.md)
- Inside: 0.875 in (for 6x9) or 0.75 in (for 5.5x8.5)
- Outside: 0.625 in (for 6x9) or 0.5 in (for 5.5x8.5)
- Top: 0.75 in
- Bottom: 0.75 in

### Fonts
- **Embed all fonts** (fully, not subsets)
- Body: Georgia or Garamond, 11pt
- Chapter titles: same family, small caps, 18pt
- **Minimum text size**: 7pt

### Images
- **300 DPI minimum** for all images
- Flatten transparent objects/layers
- Embed in file, don't link

### Lines/Graphics
- **Minimum line weight**: 0.75pt / 0.01" / 0.3mm
- Grayscale fill minimum: 10% (for black ink + white/cream paper)

### What NOT to Include
- No crop marks, trim marks, bookmarks
- No comments, annotations, placeholder text
- No metadata, invisible objects
- No PDF creation logos or watermarks
- No file locks or encryption
- No template text (must be customized or removed)

### Manual Review Checklist
- [ ] Title page matches book details exactly
- [ ] Copyright page matches
- [ ] Headers/footers match
- [ ] Page numbers sequential (even=left, odd=right)
- [ ] No more than 4 consecutive blank pages (beginning/middle)
- [ ] No more than 10 consecutive blank pages (end)
- [ ] All text legible (7pt minimum)
- [ ] No text cut off by margins
- [ ] No template text remaining
- [ ] No "bundled set" language
- [ ] No binding terms (spiral, hardbound, leather, calendar)
- [ ] Spine text needs 79+ pages and 0.0625" margin on each side

### PDF Creation Best Practice
1. Use PDF/X-1a format
2. Disable image downsampling
3. Remove watermarks
4. Optimize for reduced file size
5. Create NEW file each time (don't save over old versions — prevents corruption)
6. Open and verify PDF looks correct before uploading

### Our Build Command (future)
```bash
# When we build the paperback:
python scripts/publish/build_paperback_pdf.py --trim 5.5x8.5 --font Georgia --embed-fonts
```

### Current Status
- Ebook (EPUB): DONE, uploaded to KDP
- Paperback (PDF): NOT YET BUILT — needs PDF generation script with proper margins, fonts, pagination
