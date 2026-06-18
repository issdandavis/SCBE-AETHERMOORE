# KDP Bookforge Checklist

Use this before uploading a Kindle eBook, paperback, or hardcover to Amazon KDP.

This is a working checklist, not legal advice. Verify the linked KDP pages before upload because Amazon can change requirements.

## 1. Book Facts

- [ ] Title, subtitle, series, author, contributors, language, description, categories, keywords, and age/range fields are ready.
- [ ] Decide whether the final book contains AI-generated text, images, or translations.
- [ ] If the final book contains AI-generated text, images, or translations, disclose that in KDP's AI-generated content section.
- [ ] If AI only helped with brainstorming, editing, outlining, or proofreading and you created the final content yourself, treat it as AI-assisted, not AI-generated, per KDP's distinction.

Source: <https://kdp.amazon.com/help/topic/G200672390>

## 2. Manuscript

- [ ] Pick trim size before final layout.
- [ ] Decide whether the print book uses bleed.
- [ ] Set margins and gutter for the chosen trim/page count.
- [ ] Check every image intended for print at 300 DPI or better.
- [ ] For eBook upload, do not include the cover image inside the manuscript file; KDP adds the cover during title setup.

Sources:

- <https://kdp.amazon.com/help/topic/GVBQ3CMEQW3W2VL6>
- <https://kdp.amazon.com/help/topic/G202169030>
- <https://kdp.amazon.com/help?topicId=G200645680>

## 3. Print Cover

- [ ] Final interior page count is known before building the cover wrap.
- [ ] Paperback/hardcover cover is one PDF containing back cover, spine, and front cover.
- [ ] Add bleed to the full cover size.
- [ ] Do not include spine text unless the print book has more than 79 pages.
- [ ] If spine text is used, leave at least 0.0625 in / 1.6 mm between text and spine edge.
- [ ] Check final cover in KDP Print Previewer.

Sources:

- <https://kdp.amazon.com/help/topic/G201953020>
- <https://kdp.amazon.com/help/topic/G201857950>
- <https://kdp.amazon.com/cover-templates>

## 4. Cover Art Workflow

- [ ] Extract the cover scene from the book: setting, motif, core emotion, genre shelf, and one visual object.
- [ ] Generate 4-8 rough thumbnail directions before committing to a final cover.
- [ ] Generate cover art without text, author name, subtitle, fake barcode, or watermark.
- [ ] Pick one rough direction before final detail generation.
- [ ] Generate front art, spine/back texture, and background extension as separate layers when possible.
- [ ] Add title, subtitle, author, spine text, back-cover blurb, and barcode safe area in layout, not inside the image model.
- [ ] Keep the final print wrap tied to final page count; page count changes spine width.

## 5. Kindle eBook Cover

- [ ] Cover is JPEG or TIFF.
- [ ] Ideal image size is 2560 x 1600 px.
- [ ] Minimum image size is 1000 px high and 625 px wide.
- [ ] Image does not exceed 10,000 px in height or width.
- [ ] File is under 50 MB.
- [ ] Height/width ratio is at least 1.6:1.

Source: <https://kdp.amazon.com/help/topic/G200645690>

## 6. Bookforge Commands

```powershell
bookforge info bookforge.json
bookforge interior bookforge.json
bookforge cover bookforge.json
bookforge epub bookforge.json
bookforge docx bookforge.json
bookforge build bookforge.json
```

Use `bookforge info` first. Page count controls the print cover spine width, so the interior has to stabilize before the final cover wrap.
