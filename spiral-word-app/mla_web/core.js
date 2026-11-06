/* Shared offline document contract. No provider calls, analytics, or dependencies. */
(function (root) {
  'use strict';
  const fields = [
    'firstName',
    'lastName',
    'instructor',
    'course',
    'date',
    'title',
    'body',
    'works',
  ];
  const months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];
  function clean(input) {
    const d = {};
    for (const k of fields)
      d[k] = typeof input[k] === 'string' ? input[k].replace(/\r\n?/g, '\n') : '';
    if (Object.values(d).some((v) => v.length > 200000))
      throw Error('A field is too large (200,000 character limit).');
    return d;
  }
  function dateText(s) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return '';
    const [y, m, d] = s.split('-').map(Number),
      value = new Date(Date.UTC(y, m - 1, d));
    if (value.getUTCFullYear() !== y || value.getUTCMonth() !== m - 1 || value.getUTCDate() !== d)
      return '';
    return `${d} ${months[m - 1]} ${y}`;
  }
  function validate(input) {
    const d = clean(input),
      checks = [];
    for (const [field, label] of [
      ['firstName', 'First name'],
      ['lastName', 'Last name'],
      ['instructor', 'Instructor'],
      ['course', 'Course'],
    ])
      checks.push({
        id: field,
        ok: !!d[field].trim(),
        label: `${label} in the first-page heading`,
      });
    checks.push({ id: 'date', ok: !!dateText(d.date), label: 'Date: day, full month, year' });
    checks.push({
      id: 'title',
      ok: !!d.title.trim() && !/^untitled$/i.test(d.title.trim()),
      label: 'A title for your document',
    });
    checks.push({ id: 'body', ok: !!d.body.trim(), label: 'Your own practice paragraph or essay' });
    return checks;
  }
  function filename(d, template) {
    const safe = (s) =>
      s
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, '')
        .trim()
        .slice(0, 70);
    return `${safe(d.lastName) || 'LastName'}, ${safe(d.firstName) || 'FirstName'} ${template ? 'My MLA Template' : safe(d.title) || 'Essay'}.docx`;
  }
  const xml = (s) =>
    s
      .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  const ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  const relns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
  const pr =
    '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>';
  const spacing =
    '<w:spacing w:before="0" w:after="0" w:line="480" w:lineRule="auto"/><w:contextualSpacing/>';
  function paragraph(text, kind = 'plain') {
    const props =
      spacing +
      `<w:jc w:val="${kind === 'title' ? 'center' : 'left'}"/>` +
      (kind === 'body'
        ? '<w:ind w:firstLine="720"/>'
        : kind === 'citation'
          ? '<w:ind w:left="720" w:hanging="720"/>'
          : '<w:ind w:left="0" w:firstLine="0"/>');
    return `<w:p><w:pPr>${props}</w:pPr><w:r>${pr}<w:t xml:space="preserve">${xml(text)}</w:t></w:r></w:p>`;
  }
  function parts(input) {
    const d = clean(input);
    const failed = validate(d).filter((c) => !c.ok);
    if (failed.length) throw Error('Complete: ' + failed.map((c) => c.id).join(', '));
    const heading = [
      `${d.firstName.trim()} ${d.lastName.trim()}`,
      d.instructor.trim(),
      d.course.trim(),
      dateText(d.date),
    ];
    let body = heading.map((t) => paragraph(t)).join('') + paragraph(d.title.trim(), 'title');
    body += d.body
      .split('\n')
      .filter((s) => s.trim())
      .map((s) => paragraph(s.trim(), 'body'))
      .join('');
    if (d.works.trim()) {
      body += `<w:p><w:pPr>${spacing}<w:pageBreakBefore/><w:jc w:val="center"/></w:pPr><w:r>${pr}<w:t>Works Cited</w:t></w:r></w:p>`;
      body += d.works
        .split('\n')
        .filter((s) => s.trim())
        .map((s) => paragraph(s.trim(), 'citation'))
        .join('');
    }
    const section =
      '<w:sectPr><w:headerReference w:type="default" r:id="rHeader"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/><w:pgNumType w:start="1"/></w:sectPr>';
    const types = ['document', 'styles', 'settings', 'header1']
      .map(
        (n) =>
          `<Override PartName="/word/${n}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.${n === 'document' ? 'document.main' : n === 'header1' ? 'header' : n}+xml"/>`
      )
      .join('');
    const declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
    return {
      '[Content_Types].xml':
        declaration +
        `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>${types}</Types>`,
      '_rels/.rels':
        declaration +
        `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rDoc" Type="${relns}/officeDocument" Target="word/document.xml"/></Relationships>`,
      'word/document.xml':
        declaration +
        `<w:document xmlns:w="${ns}" xmlns:r="${relns}"><w:body>${body}${section}</w:body></w:document>`,
      'word/header1.xml':
        declaration +
        `<w:hdr xmlns:w="${ns}"><w:p><w:pPr>${spacing}<w:jc w:val="right"/></w:pPr><w:r>${pr}<w:t xml:space="preserve">${xml(d.lastName.trim())} </w:t></w:r><w:fldSimple w:instr=" PAGE "><w:r>${pr}<w:t>1</w:t></w:r></w:fldSimple></w:p></w:hdr>`,
      'word/styles.xml':
        declaration +
        `<w:styles xmlns:w="${ns}"><w:docDefaults><w:rPrDefault>${pr}</w:rPrDefault><w:pPrDefault><w:pPr>${spacing}</w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>${pr}<w:pPr>${spacing}</w:pPr></w:style></w:styles>`,
      'word/settings.xml':
        declaration + `<w:settings xmlns:w="${ns}"><w:updateFields w:val="true"/></w:settings>`,
      'word/_rels/document.xml.rels':
        declaration +
        `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${[
          ['rHeader', 'header', 'header1'],
          ['rStyles', 'styles', 'styles'],
          ['rSettings', 'settings', 'settings'],
        ]
          .map(([id, t, f]) => `<Relationship Id="${id}" Type="${relns}/${t}" Target="${f}.xml"/>`)
          .join('')}</Relationships>`,
    };
  }
  function zip(files) {
    const enc = new TextEncoder(),
      blocks = [],
      central = [];
    let offset = 0;
    const crc = (bytes) => {
      let c = 0xffffffff;
      for (const b of bytes) {
        c ^= b;
        for (let j = 0; j < 8; j++) c = (c >>> 1) ^ (c & 1 ? 0xedb88320 : 0);
      }
      return (c ^ 0xffffffff) >>> 0;
    };
    const header = (size, values) => {
      const a = new Uint8Array(size),
        v = new DataView(a.buffer);
      for (const [off, n, width] of values)
        width === 2 ? v.setUint16(off, n, true) : v.setUint32(off, n, true);
      return a;
    };
    for (const [path, text] of Object.entries(files)) {
      const name = enc.encode(path),
        data = enc.encode(text),
        check = crc(data);
      const local = header(30, [
        [0, 0x04034b50],
        [4, 20, 2],
        [6, 0x800, 2],
        [12, 33, 2],
        [14, check],
        [18, data.length],
        [22, data.length],
        [26, name.length, 2],
      ]);
      const directory = header(46, [
        [0, 0x02014b50],
        [4, 20, 2],
        [6, 20, 2],
        [8, 0x800, 2],
        [14, 33, 2],
        [16, check],
        [20, data.length],
        [24, data.length],
        [28, name.length, 2],
        [42, offset],
      ]);
      blocks.push(local, name, data);
      central.push(directory, name);
      offset += local.length + name.length + data.length;
    }
    const cdSize = central.reduce((n, a) => n + a.length, 0),
      count = Object.keys(files).length;
    const end = header(22, [
      [0, 0x06054b50],
      [8, count, 2],
      [10, count, 2],
      [12, cdSize],
      [16, offset],
    ]);
    const out = new Uint8Array(offset + cdSize + 22);
    let n = 0;
    for (const a of [...blocks, ...central, end]) {
      out.set(a, n);
      n += a.length;
    }
    return out;
  }
  function pluginRules(plugin, d) {
    if (
      !plugin ||
      plugin.schema !== 'spiralword.rules.v1' ||
      typeof plugin.name !== 'string' ||
      !Array.isArray(plugin.rules) ||
      plugin.rules.length > 20
    )
      throw Error('Use a Spiral Word rules plugin (maximum 20 rules).');
    return plugin.rules.map((r) => {
      if (
        !fields.includes(r.field) ||
        !['required', 'minWords', 'maxWords', 'equals'].includes(r.op) ||
        typeof r.label !== 'string' ||
        r.label.length > 160
      )
        throw Error('Unsupported plugin rule.');
      if (
        ['minWords', 'maxWords'].includes(r.op) &&
        (!Number.isInteger(r.value) || r.value < 0 || r.value > 100000)
      )
        throw Error('Invalid word limit.');
      if (r.op === 'equals' && (typeof r.value !== 'string' || r.value.length > 1000))
        throw Error('Invalid expected value.');
      const text = d[r.field].trim(),
        count = text ? text.split(/\s+/u).length : 0;
      return {
        id: r.field,
        label: r.label,
        ok:
          r.op === 'required'
            ? !!text
            : r.op === 'minWords'
              ? count >= r.value
              : r.op === 'maxWords'
                ? count <= r.value
                : text === r.value,
      };
    });
  }
  const api = {
    fields,
    clean,
    dateText,
    validate,
    filename,
    parts,
    zip,
    pluginRules,
    docx: (d) => zip(parts(d)),
  };
  root.SpiralMLA = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
