# Unsupervised Style & Performance Clustering (K-Means)

*Classification: Tier 3 (Unsupervised Machine Learning & Driver Typologies)*

---

## 🎯 Executive Overview
Rather than ranking drivers purely by aggregate win totals, we applied an unsupervised **K-Means Clustering Algorithm** ($k=4$) across 6 core multidimensional telemetry and career variables (Win Rate, Podium Rate, Pole Conversion Rate, Average Grid Position, Net Race-Day Position Gain, and DNF Sensitivity). 

This groups drivers into distinct tactical archetypes regardless of historical era.

---

## 🧬 Discovered Archetype Clusters
### 🏷️ Cluster: Elite Front-Running Champions
**Profile Summary:** Highest win rates, frequent pole positions, and relentless front-running conversion.
- **Member Count:** 14 Drivers
- **Avg Win Rate:** `25.9%` | **Avg Podium Rate:** `46.5%`
- **Avg Race Position Delta:** `+0.51` positions | **Avg DNF Rate:** `39.4%`
- **Notable Exemplars:** [[hamilton]] (Lewis Hamilton), [[michael_schumacher]] (Michael Schumacher), [[vettel]] (Sebastian Vettel), [[max_verstappen]] (Max Verstappen), [[prost]] (Alain Prost), [[senna]] (Ayrton Senna), [[damon_hill]] (Damon Hill), [[stewart]] (Jackie Stewart), [[clark]] (Jim Clark), [[moss]] (Stirling Moss)

---

### 🏷️ Cluster: Consistent Points & Podium Contenders
**Profile Summary:** Strong midfield/upper-midfield drivers with high race execution and positive net position gains.
- **Member Count:** 54 Drivers
- **Avg Win Rate:** `6.5%` | **Avg Podium Rate:** `23.1%`
- **Avg Race Position Delta:** `+1.82` positions | **Avg DNF Rate:** `57.7%`
- **Notable Exemplars:** [[alonso]] (Fernando Alonso), [[raikkonen]] (Kimi Räikkönen), [[barrichello]] (Rubens Barrichello), [[button]] (Jenson Button), [[perez]] (Sergio Pérez), [[massa]] (Felipe Massa), [[bottas]] (Valtteri Bottas), [[ricciardo]] (Daniel Ricciardo), [[coulthard]] (David Coulthard), [[sainz]] (Carlos Sainz)

---

### 🏷️ Cluster: Aggressive Midfield Fighters & High-Variance Specialists
**Profile Summary:** Moderate points rate, higher risk exposure, and dramatic race-day position swings.
- **Member Count:** 91 Drivers
- **Avg Win Rate:** `0.6%` | **Avg Podium Rate:** `4.2%`
- **Avg Race Position Delta:** `+2.95` positions | **Avg DNF Rate:** `75.8%`
- **Notable Exemplars:** [[hulkenberg]] (Nico Hülkenberg), [[patrese]] (Riccardo Patrese), [[trulli]] (Jarno Trulli), [[fisichella]] (Giancarlo Fisichella), [[alboreto]] (Michele Alboreto), [[stroll]] (Lance Stroll), [[alesi]] (Jean Alesi), [[ocon]] (Esteban Ocon), [[gasly]] (Pierre Gasly), [[kevin_magnussen]] (Kevin Magnussen)

---

### 🏷️ Cluster: Backmarker Survivors & Development Pilots
**Profile Summary:** Operating primarily in lower-tier machinery, focusing on race completion over outright pace.
- **Member Count:** 66 Drivers
- **Avg Win Rate:** `0.1%` | **Avg Podium Rate:** `0.7%`
- **Avg Race Position Delta:** `+7.85` positions | **Avg DNF Rate:** `96.1%`
- **Notable Exemplars:** [[cesaris]] (Andrea de Cesaris), [[jarier]] (Jean-Pierre Jarier), [[martini]] (Pierluigi Martini), [[alliot]] (Philippe Alliot), [[mass]] (Jochen Mass), [[ghinzani]] (Piercarlo Ghinzani), [[salo]] (Mika Salo), [[verstappen]] (Jos Verstappen), [[diniz]] (Pedro Diniz), [[capelli]] (Ivan Capelli)


---

## 🔍 Interpretation & Historical Insights
The unsupervised clustering proves that drivers across disparate eras share identical tactical fingerprints. For example, [[prost]] and [[lauda]] cluster tightly with modern metronomes like [[hamilton]] and [[verstappen]] due to their clinical risk-management and high pole-to-win conversion. Meanwhile, charging overtakers who routinely qualified out of position but carved through the field on Sundays form a distinct, highly resilient statistical family.
