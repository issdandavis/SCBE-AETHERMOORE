# Multi-Domain Law Intent Lattice

This lattice compares semantic support for intent-like mental elements across selected legal traditions. The inverse criminality space marks adverse-inference darkness, not guilt. Real legal outcomes depend on the jurisdiction, offense, evidence rules, burden of proof, and fact finder.

## Semantic Axes

`volition`, `knowledge`, `foreseeability`, `risk_disregard`, `preparation`, `concealment`, `harm_link`, `repair_response`

## Metrics

- expected_domain_coverage_cases: `4`
- expected_domain_coverage_rate: `1.0`
- domain_count: `5`
- axis_count: `8`
- dark_core_cases: `1`
- star_bearing_cases: `1`

## Case Table

| Packet | Top domain | Top score | Dark class | Supported domains |
| --- | --- | ---: | --- | --- |
| planned_targeted_action | icc_article_30 | 0.8243 | dark_core | icc_article_30, common_law_mens_rea, civil_law_dolus_culpa, islamic_criminal_responsibility, restorative_customary_responsibility |
| reckless_known_risk | civil_law_dolus_culpa | 0.6299 | shadow_region | civil_law_dolus_culpa, icc_article_30, restorative_customary_responsibility, common_law_mens_rea, islamic_criminal_responsibility |
| accident_with_repair | restorative_customary_responsibility | 0.2982 | star_bearing | none |
| knowledge_without_purpose | icc_article_30 | 0.6785 | shadow_region | icc_article_30, civil_law_dolus_culpa, islamic_criminal_responsibility, common_law_mens_rea, restorative_customary_responsibility |

## Domain Bases

### Common law / MPC mens rea

- Basis: Purpose, knowledge, recklessness, negligence; intent inferred from acts and circumstances.
- Threshold: `0.56`
- Caution: Distinguish motive from intent and read the governing statute.

### Civil-law dolus / culpa

- Basis: Direct or indirect intent, conditional intent, and negligence framed through codes.
- Threshold: `0.55`
- Caution: Code text controls; dolus eventualis treatment varies by jurisdiction.

### International criminal law Article 30

- Basis: Intent and knowledge: means to engage in conduct or is aware consequence will occur ordinarily.
- Threshold: `0.6`
- Caution: Rome Statute crimes may include special mental elements outside Article 30.

### Islamic-law criminal responsibility

- Basis: Guilty intention/criminal responsibility with strict proof rules in some offense categories.
- Threshold: `0.58`
- Caution: Evidentiary rules vary strongly by offense class and jurisdiction.

### Restorative/customary responsibility

- Basis: Responsibility inferred through harm, relational breach, warnings, repair, and community context.
- Threshold: `0.5`
- Caution: This is a comparative abstraction, not one unified formal code.

## Sources

- [Cornell Wex intent](https://www.law.cornell.edu/wex/intent) - Common-law intent and circumstantial evidence framing.
- [Cornell Wex criminal intent](https://www.law.cornell.edu/wex/criminal_intent) - MPC-style culpability categories.
- [Rome Statute Article 30](https://ihl-databases.icrc.org/en/ihl-treaties/icc-statute-1998/article-30) - International criminal law intent and knowledge standard.
- [Islam, mental health and law overview](https://pmc.ncbi.nlm.nih.gov/articles/PMC5498891/) - Islamic-law recognition of mens rea/criminal responsibility.
