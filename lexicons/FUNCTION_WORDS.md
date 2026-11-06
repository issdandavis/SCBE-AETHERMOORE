# Shared function words and perspectives

The six native word lists now refer to `function_primitives.json`. It contains
116 authored semantic entries: articles, determiners, prepositions, conjunctions,
pronouns, auxiliaries, particles, deixis, discourse links, speech acts and content
classes. The inventory is extensible; it is not an exhaustive universal grammar.

Existing native words, particles, roots and provenance are unchanged. The new
`function_words` section is loaded by `python.scbe.tongue_lexicon.load_full()`.
Shared English example forms are **not** inserted into the native classifier.
Native senses already present, such as Avali `nos` and `ora`, are linked explicitly.
Missing native forms stay empty. Rule-generated Draumric words retain that label.

Each semantic ID can be encoded as `scbe.fn.v1/<id>` through any of the existing
six framed STISTA lanes. A sequence is a derived codec representation, not a newly
discovered native word. No byte ID is reassigned or tokenizer vocabulary resized.
For example, `part.negation` is one shared meaning with six reversible encodings.

```python
from python.scbe.tongue_lexicon import load_full
from python.scbe.function_lexicon import resolve_reference

lex = load_full()
lex.function_meaning("that")  # determiner, pronoun AND conjunction senses
lex.function_meaning("have", family="helping_verb")
lex.functions.wordlist("AV")  # full shared inventory, native links where present

resolve_reference(lex.functions.entry("pron.addressee"), {
    "speaker": "Lina", "addressees": ["Oren"], "hearers": ["Oren", "Nell"]
})  # ["Oren"], not all hearers

space = lex.functions.compose([
    {"id": "pron.we.unspecified", "scope": "subject", "referent": "team", "weight": 1},
    {"id": "pron.we.inclusive", "scope": "subject", "referent": "team", "weight": 3},
    {"id": "part.negation", "scope": "clause"},
], perspective={"speaker": 3, "listener": 1},
   stance={"positive": 1, "negative": 1}, topic="the proposed plan")
```

Compatible descriptions share a named cell. The unspecified and inclusive group
descriptions above share `subject`, with occurrence ratios 1/4 and 3/4. Distinct
subjects, conflicting features, and contradictory referents require separate
scopes. The caller supplies those scopes; this is not an automatic prose parser.

For nonnegative masses `m_i`, the exact mixture is `p_i = m_i / sum(m_j)`.
Ratios such as `"0.0001"` remain rational values, rather than being rounded away.
At least one mass must be positive. Negative emphasis is represented by a
separate **negative stance channel**, never by a negative probability.

| Field | Meaning | What a weight cannot change |
|---|---|---|
| Grammar polarity | Affirmation or negation in an explicit scope | A positive stance cannot remove `not` |
| Stance | Negative, neutral, positive emphasis about a named topic | Does not certify truth or emotional state |
| Speaker | Source of this utterance | Does not establish authority or truth |
| Addressee | Intended recipient | Is not automatically every hearer |
| Hearer | Someone recorded as hearing | Does not establish attention or comprehension |
| Listener | Someone recorded as attending | Does not establish agreement or consent |
| Bystander | Present observer, including a quiet "wallflower" | Quietness does not imply absence of knowledge |
| Nonparticipant | Outside the active exchange | No knowledge is inferred merely from the label |
| Omniscient narrator | View over supplied story facts | Never grants those facts to a character |

`perspective_views(facts, role_entities, ratios)` returns separately attributed
views; it never takes the union and pretends every participant knows everything.
Each fact supplies `id`, `text`, `known_by` and `status`. Status distinguishes
observed, reported, hypothetical and fictional records. The narrator can only
report supplied records, with their status retained. This API is a story-context
projection, not an authentication or confidentiality boundary for untrusted code.

Unbound references return an empty list. Inclusive and exclusive `we` require an
explicit group and addressee frame. Nested quotation requires a new frame; it does
not silently reuse the outer speaker. Spelling lookup returns all senses, including
content/function ambiguity; ratios cannot select the truth of an ambiguous claim.

## Clay ingestion and evidence

Next-run bundle:
`C:/dev/tongue-compiler/artifacts/function_perspective_20260924/bundle_v2`.
Its `word_catalog.csv` is the compact human-readable list; `six_tongue_wordlists.json`
contains the actual codec sequences and native links. Its compiler exposes
`training_pools` and `attach_to_predecessor`, retaining inherited rehearsal slots.
Only `model_prompt` is an input field; targets and evaluation metadata stay separate.

The packet is prepared for a new sealed continuation. It is not injected into an
already-running experiment. Codec roundtrips establish representation consistency;
learning requires an actual subsequent training run and held-out comparison.

## Linguistic sources

- [Universal Dependencies POS](https://universaldependencies.org/u/pos/index.html):
  distinguish word classes from their grammatical features.
- [UD Polarity](https://universaldependencies.org/u/feat/Polarity.html): grammatical
  negation is distinct from sentiment and from negative pronouns.
- [UD DeixisRef](https://universaldependencies.org/u/feat/DeixisRef.html): location
  references can depend on speaker or hearer. Attention/narrator fields here are
  application-specific metadata, not claimed UD features.
- [WALS, inclusive/exclusive pronouns](https://wals.info/chapter/39): use explicit
  inclusion when English `we` alone leaves the group ambiguous.

The user's ENGL&101 material supplies the pedagogical content/function distinction
and fixed-content connector exercises. The new examples are original. Numerals
are content under that course convention while retaining UD `NUM`; taxonomy and
context can differ. No claim is made that all languages use these English forms
or the same division into separate words.
