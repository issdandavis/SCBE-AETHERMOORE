# Qi And Combat Engine Notes

Status: working research adapter  
Purpose: make combat in the Watershed book feel like cultivation without turning it into a stats log.

Companion note: `qi-in-lit-anime-manhwa.md` tracks genre research across cultivation novels, anime power systems, and murim manhwa.

## Source Ground

Qi is usually translated through breath, vapor, vital force, or life-force. For this book, the useful craft point is not whether Qi is "energy" in a modern physics sense. The useful point is that Qi is the cultivator's life-blood: breath, circulation, stored years, appetite, heat, recovery, inheritance, and the body's wager against an ordinary death.

A cultivator does not simply gain power. They trade the shape of a normal life for another one. They eat differently. Sleep differently. Age differently. Heal differently. They damage themselves in ways common people cannot see and preserve themselves in ways common people cannot imagine. Longevity is not a prize sitting at the end of cultivation. It is the long consequence of remaking the body around Qi until the old bargain no longer applies.

That makes Qi intimate. A fighter's Qi is not only what they spend. It is what their body has become.

Wuxing is better treated as Five Phases than five inert elements. Britannica and the Internet Encyclopedia of Philosophy both frame wuxing as process-oriented: water descends, fire rises, wood bends and straightens, metal yields and changes, earth receives and gives. That matters for Fenshui Zong because the sect is not interested in element-as-color. It is interested in transition.

For combat, that gives us a cleaner rule:

Qi is not ammunition first. Qi is life under cultivation.

It behaves under pressure, but the behavior matters because the thing under pressure is the cultivator's altered life. A bad expenditure is not just a low battery. It is a shortened breath, a meridian bruise, a recovery debt, a tremor that may be gone by morning or may still be there when the tournament comes.

## Cultivator Bargain

Normal people spend life by living it.

Cultivators spend life by refining it.

That is the bargain under every technique. A cultivator takes food, breath, sleep, pain, weather, fear, discipline, and time, then pushes those things through the root until the body becomes less normal and more capable. This is why villagers look at cultivators with admiration and unease. A cultivator has not merely learned a skill. They have entered a different contract with their own flesh.

The book should treat Qi expenditure in three layers:

- immediate: heat, breath, balance, pain, clarity, recovery
- bodily: meridian strain, organ heat, joint dryness, appetite, sleep debt, scar behavior
- life-scale: longevity gained, longevity risked, ordinary life abandoned, future capacity preserved or damaged

Small techniques may only touch the immediate layer. Forbidden techniques should touch all three.

This is also why elders are frightening even when they are not dramatic. An elder has had more years to turn living into stored capacity. Their stillness is not emptiness. It is accumulated life that does not need to announce itself.

## Watershed Interpretation

Standard sects measure root purity, output, and control. That makes sense for tournament brackets and military recruitment. It does not fully describe what the Watershed Sect studied.

Watershed cultivation cares about:

- flow: what a force is already doing
- obstruction: where a force catches
- transition: when one state becomes another
- resonance: whether multiple bodies can hold a shared pattern
- cost: what a technique asks from breath, joint, attention, pride, fear, and time
- preservation: what part of a cultivated life must remain unspent

This keeps the system grounded. Nobody should say a paragraph about "the river of destiny" when the useful fact is that damp wood swells, a stair has shifted, or a boy's breathing changed before he lied.

## Character Qi Rules

### Pei Yun Zhou

His Wind-Water root is scattered. That remains true.

Combat engine rule: do not give him higher Qi numbers to make him special. Give him board-state and terrain advantages. He notices pressure changes before they become visible. In engine terms, his gift belongs in `terrain.modifiers`, feature ordering, and Go-board probe/study events more than raw `stats.qi`.

Preferred outputs:

- moves early, not strongly
- wins position before winning exchange
- cannot explain why a spot is wrong
- gets punished if he tries to overpower someone

### Su Yu Ping

Her Fire is clean, strong, and disciplined.

Combat engine rule: high `stats.qi`, strong technique momentum, but strict terrain constraints. Fire in a dry courtyard is authority. Fire in a rotten wet corridor is liability. Her training is real; the scene should not make her wrong just so Yun Zhou can be right.

Preferred outputs:

- decisive first tactic
- excellent control when the target is still
- frustration when the field refuses to become simple
- growth through restraint, not nerfing

### Pei Nuan Shi

Her Earth is not combat-first.

Combat engine rule: she should enter through features and terrain, not duel dominance. She reads anchors, stress, seal fatigue, reagent residue, and load-bearing lies. In Go-board terms she is a qi-node and protected-zone character.

Preferred outputs:

- stops fights by naming what will break
- changes the objective from win to preserve
- earns authority through exact material facts

### Chen Da Shi

His Earth and body refinement make him durable, but his real combat value is interruption.

Combat engine rule: high `body`, moderate `qi`, low technique variety. He should absorb pressure, block removal, and turn a bad exchange into a survivable one. His best beats are not "big hit"; they are "someone did not get taken."

Preferred outputs:

- moves before deciding when a person is being removed
- can hold a line longer than he can explain
- learns precision as a harder form of strength

### Lin Sui Yue

Weak Wood-Metal does not become secret god-tier.

Combat engine rule: low combat stats, high feature/study value. He should improve the group's path by reading inscriptions, formations, intention, and contradictions. In Go-board terms, he is the governed-study lane.

Preferred outputs:

- knows the one fact nobody else knows
- hesitates too long early
- learns that information only counts when acted on

### Jiang Shuang

Her Qi should remain hard to classify.

Combat engine rule: do not expose full stats early. Represent her through concealed techniques, probe events, and abnormal defensive outcomes. The engine can track a hidden card without making the narration explain it.

Preferred outputs:

- moves less than others
- wastes less motion
- reveals something true, not everything

## Engine Mapping

Use the existing `src/narrative_combat` system instead of building a new combat engine.

The maze-style engine is good for duel scenes:

- `Fighter.stats.qi` = available cultivated life-output in the scene, not destiny
- `Fighter.stats.focus` = composure, reading, discipline
- `Technique.cost` = immediate draw against breath, meridian strain, and recovery debt
- `Feature.kind` = what the scene tests
- `Terrain.constraints` = hard walls the prose may not violate
- `PlannedGoal.price` = why a win remains legible without HP

The Go-board engine is good for group fights, ruin exploration, formations, crowds, and tournament pressure:

- stones = positions, committed bodies, or held ground
- liberties = escape routes, breath, available choices
- qi nodes = available cultivated force in the environment, not free power
- capture = position overrun, not automatic death
- treaty = protected ground, social agreement, formation lock, or rescue boundary
- study = Sui Yue/Nuan Shi style research moment under pressure

## Generator Improvements We Need

1. Project fixture layer

Create Watershed-specific encounters that feed existing mechanics with this book's characters, roots, and constraints.

2. Character stat philosophy

Do not rank everyone on one ladder. Some characters should have low raw Qi and high feature leverage. That is the whole point of Fenshui Zong.

3. Group resonance objective

Add objective types where the goal is not defeat: open, preserve, rescue, stabilize, expose, delay, pass together.

4. Translation guardrails

The prose renderer should not say "spending 3 qi" in manuscript mode. It should render cost as breath catching, heat thinning, a wrist shaking, a stance losing root, hunger arriving too soon, sleep becoming thin, a scar warming, a thought arriving late, or an elder noticing that a child has spent tomorrow's steadiness to survive today.

5. Reroll value

Soft reroll should change tactical path. Hard reroll should change the scene's moral or practical objective. The best use is not "make random fight"; it is "show me three legal ways this scene can pressure the same character truth."

6. Murim consequence fields

A generated fight should carry at least one social consequence, not only a tactical result. Add fields like:

```json
{
  "murim_consequence": {
    "recognition": "Bright Mirror elder recognizes the footwork as Watershed-derived",
    "inheritance_pressure": "the archive method can no longer be treated as abandoned",
    "status_shift": "Yu Ping stops calling Yun Zhou undisciplined in public",
    "risk": "repeated use may scar the Water channel before Foundation Establishment"
  }
}
```

If a fight only answers who won, it is not doing enough work for this book. It should also change what the martial world thinks the child is allowed to become.

## Scene Rule

A fight should prove one thing, not everything.

If Yun Zhou reads the floor, do not also make him brilliant at theory. If Yu Ping burns cleanly, do not make her emotionally wrong by default. If Da Shi saves someone, do not stop to explain loyalty. Let the body arrive first.

## Sources

- Britannica, "Wuxing": https://www.britannica.com/topic/wuxing
- Britannica, "Taoism: Basic concepts": https://www.britannica.com/topic/Taoism/Basic-concepts-of-Taoism
- Britannica, "Meridian: Chinese medicine": https://www.britannica.com/science/meridian-Chinese-medicine
- Internet Encyclopedia of Philosophy, "Wuxing": https://iep.utm.edu/2012/wuxing/
