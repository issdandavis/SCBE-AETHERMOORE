# Patent Game Roles

This roster extends the SCBE patent field model with an announcer and a crowd.

The crowd is not legal authority. It is a panel of small/free models used for
cheap random opinions: what sounds confusing, what looks too broad, what a naive
reader might misunderstand, and how someone might design around a claim.

## Authority Stack

1. Official USPTO/MPEP sources and filed documents.
2. Umpire rulebook.
3. Code/spec/figure evidence.
4. Pitcher, batter, scientist, mathematician.
5. Announcer and crowd.

The announcer and crowd never decide the claim. They only create signals.

## Roles

| Role | Job |
|---|---|
| Announcer | Explains each round in plain language. |
| Umpire | Applies 101, 102, 103, 112, and filing boundaries. |
| Pitcher | Defines the invention feature technically. |
| Batter | Broadens claim coverage for the client. |
| Scientist | Checks make/use support. |
| Mathematician | Checks formula consistency and bounds. |
| Crowd | Many small models giving short outside reactions. |

## Crowd Use

Use the crowd when:

- claim language sounds clever but may be unclear;
- a feature may be too broad;
- a design-around risk is suspected;
- the drafter wants noisy outside reactions before tightening language.

Do not use the crowd as:

- legal advice;
- prior-art authority;
- final support decision;
- substitute for the filed provisional text.

## Small Model Contract

Each fan model gets the same compact prompt:

```text
You are one advisory crowd voice in a patent drafting game.
You are not authority.
Feature under review: <ball>
Draft language: <claim text>
Evidence summary: <support summary>
Give one short reaction:
- what is confusing,
- what may be too broad,
- what design-around you notice,
- or say okay if it reads clear.
Return <= 80 words with one risk_tag.
```

## Round Output

Each round should produce:

- ball;
- announcer summary;
- pitch;
- hit;
- umpire call;
- crowd signals;
- next action.
