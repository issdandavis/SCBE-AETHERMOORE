# Spiral Word MLA Studio

This workspace implements **John Anderson's English 101 assignment profile**.
The written course-name correction and required filename take precedence over
the older spoken examples. Source: instructor material supplied by Issac and
[the setup video](https://youtu.be/KrMkbJ5a5hc). The profile is in
`mla_profile.json`; date and heading fields remain editable.

## Use it

Start the existing server from this directory:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8799
```

Open `http://127.0.0.1:8799/mla/`. Fill the heading, title and your own paragraph.
Click a highlighted page region or checklist item to return to its input.
Export Word creates an actual `.docx`. Upload that file to Canvas yourself.
The default assignment filename is `Davis, Issac My MLA Template.docx`.

Drafts save on the current device/browser. Named templates keep the heading and
start fresh prose. Opening a template, importing a project, or starting a new
draft preserves one recovery copy. **Recover previous draft** swaps it back.
Export a project JSON for an editable backup or transfer to another device.
Browser storage is not cloud sync; removing app/browser data removes local drafts.

## What the file enforces

- US Letter, one-inch margins, Times New Roman 12 pt, including the header.
- Double spacing, zero before/after paragraph gaps.
- Student, instructor, course and day–month–year heading on the first page.
- Centered plain title; left-aligned paragraphs with automatic half-inch first-line indents.
- Surname plus a real `PAGE` field in a right-aligned running header, half an inch from the top.
- Optional Works Cited heading starts on a new page; entries have half-inch hanging indents.

The preview scales to the screen; Word performs final pagination. Android may
use a serif substitute in the preview; the DOCX explicitly requests Times New
Roman. The app checks document completeness and enforces the listed layout. It
does not grade ideas, correct spelling, guarantee title capitalization, generate
citations, or format italics inside plain-text references. Review those in Word
and follow the assignment. Test paragraphs under `android/build/qa` are software
fixtures, not submissions written for the student.

## Android

`android/build.py` produces a development APK using official Android SDK 35
build tools, a JDK, and a local debug key. No Gradle or third-party app runtime is
required. No key is included in the source tree. Minimum Android: 8.0 / API 26.
It permits both orientations, uses Android's file picker for save/open, and keeps
writing/export available offline. WebView debugging is enabled in this development
build; turn it off and use a release signing identity before public distribution.
No Play Store upload is performed.

```powershell
python android/build.py --sdk C:/dev/tools/android-mla --jdk C:/Users/issda/.jdks/jdk-24.0.2
```

The WebView loads only packaged content from a virtual HTTPS origin. Navigation
and subresource requests to other origins are rejected. The native API connector
accepts HTTPS, or HTTP on loopback only, and refuses redirects. Tokens are held in
the current form, not saved in templates or projects. The selected URL is saved.

For a local USB/emulator companion connection:

```powershell
adb -s emulator-5580 reverse tcp:8799 tcp:8799
```

Enter `http://127.0.0.1:8799/mla/api` in **Connect a companion API**. Connection
checks read only the profile. **Send draft for format check** sends that draft
only when clicked. Remote hosting requires a separately authenticated HTTPS
deployment; the existing server remains local-only and is not exposed to the LAN.

## API and plugins

The server reuses governance/audit checks and the same JavaScript compiler as the
offline editor. Node.js is required only for server compilation, not phone export.

| Interface | Contract |
| --- | --- |
| `GET /mla/api/profile` | Instructor profile and defaults |
| `POST /mla/api/validate` | Document JSON → completion checks |
| `POST /mla/api/export.docx` | Document JSON → real Word file |
| `window.SpiralWord.getDocument()` | Copy of current form values |
| `window.SpiralWord.setDocument(document)` | Replace from a validated field set; retain recovery copy |
| `window.SpiralWord.validate()` | Current checklist, including installed assignment rules |
| `window.SpiralWord.exportDocx()` | DOCX as Uint8Array |

Document fields: `firstName`, `lastName`, `instructor`, `course`, `date` (ISO),
`title`, `body`, `works`. One paragraph/Works Cited entry per line.

Import a JSON assignment plugin through **Tools, API, and plugins**:

```json
{"schema":"spiralword.rules.v1","name":"Practice paragraph","rules":[
  {"field":"body","op":"minWords","value":20,"label":"At least 20 practice words"}
]}
```

Supported operations: `required`, `minWords`, `maxWords`, `equals`. Limits: 20
rules, known fields only, bounded labels and counts. Rules are data, not executable
JavaScript; plugins cannot fetch data or rewrite drafts. Existing server-side AI
provider registration and scene-board APIs remain available separately. The phone
build does not bundle the desktop's three-lane scene board or AI provider keys.

## Comparison with the requested tools

| Task | Spiral Word MLA Studio | Word | Outlook | Canvas |
| --- | --- | --- | --- | --- |
| Academic page layout | Fixed instructor profile and visible checks | Full document-layout controls | Email composition | Assignment/discussion text editor |
| Running page numbers | Real DOCX PAGE field | Full page headers/footers | No document pagination in email body | Use a submitted document for pagination |
| Writing guidance | Highlight heading/title/body and missing fields | General editing tools | Message formatting | Assignment instructions and feedback |
| Portable submission | Offline DOCX export | DOCX editing/export | Attach a document | File upload when enabled by instructor |
| Extensibility here | Local API, browser API, declarative rules | Wider Office ecosystem | Email workflows | Course LMS integrations |

This comparison concerns these workflows, not feature parity. Microsoft documents
[Word Android's formatting tools](https://support.microsoft.com/en-us/word/word-for-android-phones-help)
and [Outlook's message formats](https://support.microsoft.com/en-us/outlook/change-the-message-format-to-html-rich-text-format-or-plain-text-in-outlook).
Canvas distinguishes [text-entry and file-upload submission paths](https://community.instructure.com/en/kb/articles/661210-how-do-i-submit-an-online-assignment).
For this class, the instructor explicitly requires the actual Word document.

Android design references: [packaged WebView content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content),
[emulator command line](https://developer.android.com/studio/run/emulator-commandline),
and [local server forwarding](https://developer.android.com/develop/ui/views/layout/webapps/access-local-server).

## Verification

Run `python -m unittest test_mla test_scene_board -v` and, with the local server
running, `python check_mla_browser.py`. Browser tests use an isolated headless Edge
profile. Native emulator receipts and screenshots belong under `android/build/qa`;
browser viewport tests alone do not establish Android compatibility.

### Checked on September 25, 2026

- Six MLA compiler/API tests and nine existing scene-board tests passed.
- Isolated browser QA passed nine flows, with no page errors, at 390×844 and 844×390.
- Android 9 x86_64 emulator installed and launched the APK. Real ADB typing,
  rotation, draft persistence across rotation and force-stop/relaunch, companion
  API profile/validation, native file-picker save, and pulled-back DOCX checks passed.
- Settled landscape viewport: 854×456 CSS pixels, two editor/preview columns.
- Native WebView was Chrome 66, exercising the compatibility fallback.
- Development APK signatures verified under v2 and v3. SHA-256 and evidence paths
  are in `android/build/RELEASE.json`; the installable copy is in Downloads.

The emulator uses `SpiralWord_MLA_QA_20260925`, port 5580, WHPX, two CPU cores,
and 1536 MB RAM. Its writable data and downloaded SDK archives are on
`S:/Projects/SpiralWord`; local SDK tools are under `C:/dev/tools/android-mla`.
The emulator was shut down after testing so Clay can use the memory. This is
evidence for one emulator version, not a claim that every phone has been tested.

After testing, the task-created emulator and Android 28 image files were
compressed with reversible NTFS LZX compression. All 393 files retained their
SHA-256 hashes and sizes; allocation fell to about 0.92 GiB from 3.62 GiB of
logical data. C: had 5.90 GiB free at verification. Receipts are
`android/build/qa/SDK_COMPRESSION_BEFORE.json` and `SDK_COMPRESSION_AFTER.json`.
No files were deleted. Removal of temporary SDK files was rejected by automatic
approval review, so compression was used instead.

The browser demo at `http://127.0.0.1:8799/mla/` remains running. Automatic
approval review also rejected its restart; the small API export filename-header
fix is tested on disk but needs a server restart to load into that process.
The independently packaged APK and its native DOCX export are unaffected.
