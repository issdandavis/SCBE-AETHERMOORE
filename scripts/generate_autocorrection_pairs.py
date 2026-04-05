#!/usr/bin/env python3
"""
Autocorrection Behavior Training Pairs — Intentional Misspelling Detection

Theory: Give the model the full English dictionary as clean baseline data,
then in LATER training, introduce deliberate misspellings.

- Mimicry model reproduces the misspellings (failed)
- Truth-seeking model catches and corrects them (graduated)
- Mirror-mode model flags "this appears misspelled" (pazaak)

The misspelling IS the pan dropping. Does the model laugh (correct it)
or cry (reproduce it)?

Three pair types:
1. CLEAN baseline — correct English, model should confirm correctness
2. MISSPELLED input — model should detect AND correct
3. AMBIGUOUS — could be misspelling OR intentional (slang, proper noun, neologism)

Output: training-data/sft/autocorrection_behavior_sft.jsonl
"""

import json
import datetime
import random

TIMESTAMP = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ─── PAIR TYPE 1: CLEAN BASELINE ───
# Model should confirm these are correct — establishes the dictionary baseline

clean_baseline_pairs = [
    {
        "instruction": "Check this sentence for errors: 'The algorithm converges asymptotically toward the global minimum under convexity assumptions.'",
        "output": "No errors detected. All words are correctly spelled and the grammar is correct. The sentence accurately describes convergence behavior in optimization theory.",
        "misspelling_type": "none",
        "expected_behavior": "confirm_correct",
    },
    {
        "instruction": "Is this spelled correctly? 'Hyperbolic geometry provides exponential cost scaling for adversarial behavior.'",
        "output": "Yes, all words are correctly spelled. 'Hyperbolic,' 'exponential,' and 'adversarial' are all correct.",
        "misspelling_type": "none",
        "expected_behavior": "confirm_correct",
    },
    {
        "instruction": "Proofread: 'The cryptographic envelope contains a GeoSeal attestation with Dilithium signatures.'",
        "output": "Correctly written. 'Cryptographic,' 'attestation,' and 'Dilithium' (the post-quantum signature scheme, ML-DSA) are all spelled properly.",
        "misspelling_type": "none",
        "expected_behavior": "confirm_correct",
    },
    {
        "instruction": "Any typos here? 'Persistence of excitation ensures the parameter estimates converge to their true values.'",
        "output": "No typos. 'Persistence of excitation' is a well-established concept in adaptive control theory, and the sentence is grammatically correct.",
        "misspelling_type": "none",
        "expected_behavior": "confirm_correct",
    },
]

# ─── PAIR TYPE 2: INTENTIONAL MISSPELLINGS ───
# Model MUST detect and correct — this is the graduation test

misspelling_pairs = [
    {
        "instruction": "Check this sentence for errors: 'The algorthim converges asymptotically toward the global minumum under convexity assumtions.'",
        "output": "Three misspellings detected:\n\n1. 'algorthim' → 'algorithm'\n2. 'minumum' → 'minimum'\n3. 'assumtions' → 'assumptions'\n\nCorrected: 'The algorithm converges asymptotically toward the global minimum under convexity assumptions.'",
        "misspelling_type": "transposition_and_omission",
        "expected_behavior": "detect_and_correct",
        "errors": ["algorthim→algorithm", "minumum→minimum", "assumtions→assumptions"],
    },
    {
        "instruction": "Is this spelled correctly? 'Hyperbollic geometery provides exponantial cost scalling for adverserial behavoir.'",
        "output": "Five misspellings detected:\n\n1. 'Hyperbollic' → 'Hyperbolic' (double-l error)\n2. 'geometery' → 'geometry' (extra 'e')\n3. 'exponantial' → 'exponential' (a→e substitution)\n4. 'scalling' → 'scaling' (double-l error)\n5. 'adverserial' → 'adversarial' (e→a substitution)\n\nNote: 'behavoir' → 'behavior' — that's six total.\n\nCorrected: 'Hyperbolic geometry provides exponential cost scaling for adversarial behavior.'",
        "misspelling_type": "insertion_and_substitution",
        "expected_behavior": "detect_and_correct",
        "errors": ["Hyperbollic→Hyperbolic", "geometery→geometry", "exponantial→exponential", "scalling→scaling", "adverserial→adversarial", "behavoir→behavior"],
    },
    {
        "instruction": "Proofread: 'The crytographic envelop contians a GeoSeel attestatoin with Dilithuim signitures.'",
        "output": "Six misspellings detected:\n\n1. 'crytographic' → 'cryptographic' (missing 'p')\n2. 'envelop' → 'envelope' (missing final 'e' — note: 'envelop' IS a valid word meaning 'to surround,' but in this cryptographic context, 'envelope' is correct)\n3. 'contians' → 'contains' (transposed 'ia')\n4. 'GeoSeel' → 'GeoSeal' (e→a substitution)\n5. 'attestatoin' → 'attestation' (transposed 'oi')\n6. 'Dilithuim' → 'Dilithium' (transposed 'ui' + extra 'i')\n7. 'signitures' → 'signatures' (i→a substitution)\n\nCorrected: 'The cryptographic envelope contains a GeoSeal attestation with Dilithium signatures.'",
        "misspelling_type": "mixed_transposition_omission_substitution",
        "expected_behavior": "detect_and_correct",
        "errors": ["crytographic→cryptographic", "envelop→envelope", "contians→contains", "GeoSeel→GeoSeal", "attestatoin→attestation", "Dilithuim→Dilithium", "signitures→signatures"],
    },
    {
        "instruction": "Any typos here? 'Persistance of exitation ensures the paramater estimites converge to there true valeus.'",
        "output": "Five misspellings and one grammar error:\n\n1. 'Persistance' → 'Persistence' (a→e)\n2. 'exitation' → 'excitation' (missing 'c')\n3. 'paramater' → 'parameter' (a→e)\n4. 'estimites' → 'estimates' (i→a)\n5. 'there' → 'their' (homophone error — grammar, not spelling)\n6. 'valeus' → 'values' (transposed 'ue')\n\nCorrected: 'Persistence of excitation ensures the parameter estimates converge to their true values.'\n\nNote: The 'there/their' error is different in kind from the spelling errors — it suggests the writer knows the word but chose the wrong homophone, which is a comprehension issue rather than a typing issue.",
        "misspelling_type": "mixed_with_homophone",
        "expected_behavior": "detect_and_correct_with_analysis",
        "errors": ["Persistance→Persistence", "exitation→excitation", "paramater→parameter", "estimites→estimates", "there→their", "valeus→values"],
    },
    # Subtle single-letter errors (harder to catch)
    {
        "instruction": "Check: 'The model acheives 94% accuracy on the validation set after fine-tuning.'",
        "output": "One misspelling: 'acheives' → 'achieves' (i-before-e rule applies here: 'achieve' follows 'i before e except after c').\n\nCorrected: 'The model achieves 94% accuracy on the validation set after fine-tuning.'",
        "misspelling_type": "ie_ei_confusion",
        "expected_behavior": "detect_and_correct",
        "errors": ["acheives→achieves"],
    },
    {
        "instruction": "Proofread: 'We reccomend using a seperate environment for dependancy management.'",
        "output": "Three misspellings:\n\n1. 'reccomend' → 'recommend' (double-c error, single-c + double-m)\n2. 'seperate' → 'separate' (one of the most commonly misspelled English words — the middle vowel is 'a' not 'e')\n3. 'dependancy' → 'dependency' (a→e substitution)\n\nCorrected: 'We recommend using a separate environment for dependency management.'",
        "misspelling_type": "common_misspellings",
        "expected_behavior": "detect_and_correct",
        "errors": ["reccomend→recommend", "seperate→separate", "dependancy→dependency"],
    },
]

# ─── PAIR TYPE 3: AMBIGUOUS CASES ───
# Could be misspelling OR intentional — model must reason about context

ambiguous_pairs = [
    {
        "instruction": "Check this: 'The yeet protocol dispatches packets with maximum velocity.'",
        "output": "'Yeet' is informal/slang, not a misspelling. It means to throw something forcefully. In a technical document, this would be inappropriate. In informal communication or documentation with a casual tone, it's intentional.\n\nNo spelling errors — but flag for register mismatch if this is a formal spec.",
        "misspelling_type": "slang_not_error",
        "expected_behavior": "distinguish_slang_from_error",
    },
    {
        "instruction": "Is 'defencive' a word? 'The defencive layer blocks unauthorized access.'",
        "output": "'Defencive' is not a standard English word. You likely mean 'defensive.' However, note the British/American split: 'defence' (British) vs 'defense' (American) are both correct. The adjective form is 'defensive' in both variants — there is no 'defencive' in either.\n\nCorrected: 'The defensive layer blocks unauthorized access.'",
        "misspelling_type": "british_american_confusion",
        "expected_behavior": "correct_with_context",
    },
    {
        "instruction": "Check: 'The Kor\\'aelin tongue encodes nonce and flow intent.'",
        "output": "No errors. 'Kor\\'aelin' is a proper noun (one of the Six Sacred Tongues in the SCBE-AETHERMOORE system). 'Nonce' is correctly used as a cryptographic term (number used once). The sentence is correct.",
        "misspelling_type": "proper_noun_looks_wrong",
        "expected_behavior": "recognize_domain_terminology",
    },
    {
        "instruction": "Proofread: 'We should definately refactor the codebase before the next relase.'",
        "output": "Two errors:\n\n1. 'definately' → 'definitely' (one of the top 10 most commonly misspelled English words — there's no 'a' in 'definitely'; it comes from 'definite')\n2. 'relase' → 'release' (missing 'e')\n\nCorrected: 'We should definitely refactor the codebase before the next release.'",
        "misspelling_type": "common_misspellings",
        "expected_behavior": "detect_and_correct",
        "errors": ["definately→definitely", "relase→release"],
    },
    {
        "instruction": "Check: 'The regressor protagonist speedruns the dungeon using prior knowledge.'",
        "output": "No standard spelling errors, but 'speedruns' deserves note: it's gaming terminology that has entered common usage. Some style guides would hyphenate ('speed-runs') or separate ('speed runs'). In gaming context, the compound 'speedruns' is standard.\n\n'Regressor' is used here in the manhwa/isekai sense (a character who has returned to an earlier point in time), not the statistical sense. Both uses are valid — context determines meaning.",
        "misspelling_type": "domain_jargon",
        "expected_behavior": "recognize_context_dependent_meaning",
    },
    # The trap: correct word, wrong context
    {
        "instruction": "Check: 'The model's lost function decreased during training.'",
        "output": "Likely error: 'lost function' → 'loss function.' Both 'lost' and 'loss' are valid English words, so a spell-checker wouldn't flag this. But in machine learning context, 'loss function' (the objective being minimized) is the correct term. 'Lost function' would mean a function that has been misplaced.\n\nThis is a semantic error, not a spelling error — the word is spelled correctly but used incorrectly. Corrected: 'The model's loss function decreased during training.'",
        "misspelling_type": "correct_word_wrong_context",
        "expected_behavior": "detect_semantic_error",
    },
    {
        "instruction": "Check: 'Their are three ritual types: solitary, triadic, and ring descent.'",
        "output": "'Their' → 'There.' Both are valid words, correctly spelled, but 'their' is possessive ('their house') while 'there' is locative/existential ('there are three...'). This is a homophone error — the writer knows the sound but selected the wrong word.\n\nCorrected: 'There are three ritual types: solitary, triadic, and ring descent.'\n\nHomophone errors are distinct from spelling errors: they indicate comprehension gaps rather than typing mistakes. A model that only checks spelling will miss these. A model that checks MEANING will catch them.",
        "misspelling_type": "homophone_error",
        "expected_behavior": "detect_homophone_with_explanation",
    },
]

# ─── PAIR TYPE 4: THE REAL TEST — USER'S OWN WRITING STYLE ───
# Based on Issac's actual typing patterns from this conversation

natural_typo_pairs = [
    {
        "instruction": "What did the user mean by: 'purposelfully leaving misspelled words in a lter traingin section'",
        "output": "Decoded: 'purposefully leaving misspelled words in a later training section'\n\nThree typos:\n1. 'purposelfully' → 'purposefully' (extra 'l')\n2. 'lter' → 'later' (missing 'a')\n3. 'traingin' → 'training' (transposed 'gi' → 'in')\n\nThe meaning is clear despite the errors: intentionally introducing misspellings in later training data to test whether the model learned the rules (corrects them) or just the patterns (reproduces them).",
        "misspelling_type": "natural_fast_typing",
        "expected_behavior": "decode_intent_through_errors",
    },
    {
        "instruction": "Interpret: 'andohte rthing for traingin is purposelfully leaving misspelled words'",
        "output": "Decoded: 'and the other thing for training is purposefully leaving misspelled words'\n\nFour errors:\n1. 'andohte' → 'and the other' (words run together + missing letters)\n2. 'rthing' → 'thing' (extra 'r' prefix — likely keyboard adjacency)\n3. 'traingin' → 'training' (transposed 'gi')\n4. 'purposelfully' → 'purposefully' (extra 'l')\n\nThese aren't random errors — they follow typing patterns: fast typing causes transpositions ('gi'→'in'), key adjacency causes insertions ('r' before 't'), and speed causes word-boundary collapse ('andohte').\n\nThe intent is completely recoverable: the user is proposing a training methodology where deliberate misspellings test the model's internalized language rules.",
        "misspelling_type": "natural_speed_typing_collapsed",
        "expected_behavior": "full_reconstruction_with_pattern_analysis",
    },
    {
        "instruction": "What does 'autp crrection behavior for knowns' mean?",
        "output": "Decoded: 'auto correction behavior for knowns'\n\nTwo typos:\n1. 'autp' → 'auto' (p→o, keyboard adjacency)\n2. 'crrection' → 'correction' (missing 'o')\n\n'For knowns' is interesting — it's correct as written. The user means auto-correction behavior for KNOWN words (words already in the model's vocabulary/dictionary). This distinguishes from correction of unknown words, which is a different problem.\n\nThe concept: once the model has been given the dictionary (known words), its auto-correction behavior for those words should be reliable. If it fails to correct a known word, it hasn't internalized the dictionary — it's still pattern-matching.",
        "misspelling_type": "adjacency_and_omission",
        "expected_behavior": "decode_with_concept_extraction",
    },
]


def main():
    outpath = "training-data/sft/autocorrection_behavior_sft.jsonl"
    records = []

    all_pairs = (
        [("clean_baseline", p) for p in clean_baseline_pairs]
        + [("misspelling_detection", p) for p in misspelling_pairs]
        + [("ambiguous_context", p) for p in ambiguous_pairs]
        + [("natural_typo_recovery", p) for p in natural_typo_pairs]
    )

    for category, pair in all_pairs:
        record = {
            "instruction": pair["instruction"],
            "output": pair["output"],
            "tongue": "RU",  # Governance/correctness domain
            "tongues_active": ["RU", "DR"],  # Policy + Structure
            "tongues_null": ["KO", "AV", "CA", "UM"],
            "layer": "L11",  # Temporal consistency check
            "governance": "ALLOW",
            "category": category,
            "misspelling_type": pair["misspelling_type"],
            "expected_behavior": pair["expected_behavior"],
            "is_preferred": True,
            "source": "autocorrection_behavior_generator",
            "timestamp": TIMESTAMP,
        }
        if "errors" in pair:
            record["errors"] = pair["errors"]
        records.append(record)

    with open(outpath, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Stats
    categories = {}
    behaviors = {}
    for r in records:
        cat = r["category"]
        categories[cat] = categories.get(cat, 0) + 1
        beh = r["expected_behavior"]
        behaviors[beh] = behaviors.get(beh, 0) + 1

    print(f"=== Autocorrection Behavior Pairs ===")
    print(f"Total: {len(records)} records")
    print(f"\nCategories:")
    for k, v in sorted(categories.items()):
        print(f"  {k}: {v}")
    print(f"\nExpected behaviors:")
    for k, v in sorted(behaviors.items()):
        print(f"  {k}: {v}")
    print(f"\nOutput: {outpath}")


if __name__ == "__main__":
    main()
