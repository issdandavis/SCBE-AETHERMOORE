# Sacred Tongue Interoperability Matrix
## Source of Truth: Notion Chapter 4 + Complete Reference (v2.0)

### Canonical Prefix/Suffix Tables (from Notion Chapter 4)

#### KO — Kor'aelin (Control / Intent / Nonce)
**Frequency:** 440 Hz | **Phase:** 0 deg | **Weight:** phi^0 = 1.000

| Idx | Prefix | Binary | Suffixes: 0=or, 1=ar, 2=el, 3=al, 4=in, 5=an, 6=on, 7=en, 8=il, 9=ol, A=ul, B=ir, C=ur, D=ae, E=oe, F=ia |
|-----|--------|--------|---|
| 0 | k | 0000 | kor, kar, kel, kal, kin, kan, kon, ken, kil, kol, kul, kir, kur, kae, koe, kia |
| 1 | kr | 0001 | kror, krar, krel, kral, krin, kran, kron, kren, kril, krol, krul, krir, krur, krae, kroe, kria |
| 2 | kl | 0010 | klor, klar, klel, klal, klin, klan, klon, klen, klil, klol, klul, klir, klur, klae, kloe, klia |
| 3 | kv | 0011 | kvor, kvar, kvel, kval, kvin, kvan, kvon, kven, kvil, kvol, kvul, kvir, kvur, kvae, kvoe, kvia |
| 4 | kh | 0100 | khor, khar, khel, khal, khin, khan, khon, khen, khil, khol, khul, khir, khur, khae, khoe, khia |
| 5 | kth | 0101 | kthor, kthar, kthel, kthal, kthin, kthan, kthon, kthen, kthil, kthol, kthul, kthir, kthur, kthae, kthoe, kthia |
| 6 | kph | 0110 | kphor, kphar, kphel, kphal, kphin, kphan, kphon, kphen, kphil, kphol, kphul, kphir, kphur, kphae, kphoe, kphia |
| 7 | ks | 0111 | ksor, ksar, ksel, ksal, ksin, ksan, kson, ksen, ksil, ksol, ksul, ksir, ksur, ksae, ksoe, ksia |
| 8 | kt | 1000 | ktor, ktar, ktel, ktal, ktin, ktan, kton, kten, ktil, ktol, ktul, ktir, ktur, ktae, ktoe, ktia |
| 9 | kp | 1001 | kpor, kpar, kpel, kpal, kpin, kpan, kpon, kpen, kpil, kpol, kpul, kpir, kpur, kpae, kpoe, kpia |
| A | km | 1010 | kmor, kmar, kmel, kmal, kmin, kman, kmon, kmen, kmil, kmol, kmul, kmir, kmur, kmae, kmoe, kmia |
| B | kn | 1011 | knor, knar, knel, knal, knin, knan, knon, knen, knil, knol, knul, knir, knur, knae, knoe, knia |
| C | kw | 1100 | kwor, kwar, kwel, kwal, kwin, kwan, kwon, kwen, kwil, kwol, kwul, kwir, kwur, kwae, kwoe, kwia |
| D | ky | 1101 | kyor, kyar, kyel, kyal, kyin, kyan, kyon, kyen, kyil, kyol, kyul, kyir, kyur, kyae, kyoe, kyia |
| E | kz | 1110 | kzor, kzar, kzel, kzal, kzin, kzan, kzon, kzen, kzil, kzol, kzul, kzir, kzur, kzae, kzoe, kzia |
| F | kj | 1111 | kjor, kjar, kjel, kjal, kjin, kjan, kjon, kjen, kjil, kjol, kjul, kjir, kjur, kjae, kjoe, kjia |

#### AV — Avali (Transport / AAD / Metadata)
**Frequency:** 440 * phi Hz | **Phase:** 60 deg | **Weight:** phi^1 = 1.618

| Idx | Prefix | Binary |
|-----|--------|--------|
| 0 | v | 0000 |
| 1 | av | 0001 |
| 2 | ev | 0010 |
| 3 | iv | 0011 |
| 4 | ov | 0100 |
| 5 | uv | 0101 |
| 6 | vr | 0110 |
| 7 | vl | 0111 |
| 8 | vn | 1000 |
| 9 | vm | 1001 |
| A | vth | 1010 |
| B | vh | 1011 |
| C | vs | 1100 |
| D | vk | 1101 |
| E | vp | 1110 |
| F | vt | 1111 |

**Suffixes:** a, e, i, o, al, el, il, ol, an, en, in, on, ar, er, ir, or

#### RU — Runethic (Policy / Salt / Binding)
**Frequency:** 440 * phi^2 Hz | **Phase:** 120 deg | **Weight:** phi^2 = 2.618

| Idx | Prefix | Binary |
|-----|--------|--------|
| 0 | r | 0000 |
| 1 | ru | 0001 |
| 2 | ra | 0010 |
| 3 | re | 0011 |
| 4 | ri | 0100 |
| 5 | ro | 0101 |
| 6 | rn | 0110 |
| 7 | rm | 0111 |
| 8 | rth | 1000 |
| 9 | rk | 1001 |
| A | rp | 1010 |
| B | rs | 1011 |
| C | rt | 1100 |
| D | rv | 1101 |
| E | rh | 1110 |
| F | rl | 1111 |

**Suffixes:** n, ne, na, ni, no, nu, neth, nith, noth, nuth, nic, nec, noc, nac, nth, nk

#### CA — Cassisivadan (Compute / Ciphertext)
**Frequency:** 440 * phi^3 Hz | **Phase:** 180 deg | **Weight:** phi^3 = 4.236

| Idx | Prefix | Binary |
|-----|--------|--------|
| 0 | c | 0000 |
| 1 | ca | 0001 |
| 2 | ce | 0010 |
| 3 | ci | 0011 |
| 4 | co | 0100 |
| 5 | cu | 0101 |
| 6 | cs | 0110 |
| 7 | ct | 0111 |
| 8 | ck | 1000 |
| 9 | cp | 1001 |
| A | cm | 1010 |
| B | cn | 1011 |
| C | cv | 1100 |
| D | ch | 1101 |
| E | cth | 1110 |
| F | cph | 1111 |

**Suffixes:** as, es, is, os, us, ath, eth, ith, oth, uth, ad, ed, id, od, ud, iv

#### UM — Umbroth (Security / Redaction / Veil)
**Frequency:** 440 * phi^4 Hz | **Phase:** 240 deg | **Weight:** phi^4 = 6.854

| Idx | Prefix | Binary |
|-----|--------|--------|
| 0 | um | 0000 |
| 1 | om | 0001 |
| 2 | am | 0010 |
| 3 | em | 0011 |
| 4 | im | 0100 |
| 5 | umb | 0101 |
| 6 | ump | 0110 |
| 7 | umt | 0111 |
| 8 | umr | 1000 |
| 9 | ums | 1001 |
| A | umk | 1010 |
| B | umn | 1011 |
| C | umv | 1100 |
| D | umh | 1101 |
| E | uml | 1110 |
| F | umth | 1111 |

**Suffixes:** br, bl, br, th, ph, kh, sh, ch, ro, ra, re, ri, ru, or, ar, ir

**NOTE:** UM suffix index 0 and 2 are both "br" — this is a v1.0 collision that needs fixing!

#### DR — Draumric (Schema / Auth Tags / Structure)
**Frequency:** 440 * phi^5 Hz | **Phase:** 300 deg | **Weight:** phi^5 = 11.090

| Idx | Prefix | Binary |
|-----|--------|--------|
| 0 | dr | 0000 |
| 1 | dra | 0001 |
| 2 | dre | 0010 |
| 3 | dri | 0011 |
| 4 | dro | 0100 |
| 5 | dru | 0101 |
| 6 | drau | 0110 |
| 7 | drae | 0111 |
| 8 | droi | 1000 |
| 9 | drei | 1001 |
| A | drai | 1010 |
| B | drua | 1011 |
| C | drue | 1100 |
| D | drui | 1101 |
| E | druo | 1110 |
| F | druu | 1111 |

**Suffixes:** m, mr, ml, mn, ms, mt, mk, mp, mic, mec, mac, moc, muc, mith, meth, moth

---

## Binary Interoperability

Every token maps to exactly one byte:

```
Token → Binary:  prefix_index (4 bits) + suffix_index (4 bits) = 8 bits = 1 byte
Binary → Token:  high_nibble → prefix, low_nibble → suffix
```

### Cross-Tongue Translation

The SAME byte encodes to DIFFERENT tokens across tongues but carries the SAME binary value:

| Byte | Binary | KO | AV | RU | CA | UM | DR |
|------|--------|----|----|----|----|----|----|
| 0x00 | 00000000 | kor | va | rn | cas | umbr | drm |
| 0x2A | 00101010 | klul | eval | ranicl | ceadl | amre | dremac |
| 0xFF | 11111111 | kjia | vtor | rlnk | cphiv | umthir | druumoth |

### English Translation Layer

Each tongue domain maps to English intent:

| Tongue | Domain | English Meaning |
|--------|--------|-----------------|
| KO token | Control | "This is a command/flow instruction" |
| AV token | Transport | "This is routing/metadata" |
| RU token | Policy | "This is a rule/binding" |
| CA token | Compute | "This is encrypted data" |
| UM token | Security | "This is redacted/veiled" |
| DR token | Schema | "This is structural/tag data" |

---

## Issues Found

1. **UM suffix collision**: Index 0 and 2 are both "br" — breaks bijectivity
2. **Code drift**: src/tokenizer/ss1.ts uses DIFFERENT prefix/suffix tables than Notion v2.0
3. **Multiple versions**: At least 3 different prefix/suffix sets exist across the codebase

## Action Required

1. Fix UM suffix collision (replace index 2 "br" with unique suffix)
2. Sync ss1.ts to match Notion v2.0 canonical tables
3. Sync Python sacred_tongues.py to match
4. Run bijectivity tests after sync
