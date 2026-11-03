# Delivered widget vs saved storyboard: ratio audit

Read-only audit of immutable compiled release5, the source of the delivered screenshots. Chromium viewport390×560; explicit illustrative recipe fixture. No functionality count is used as visual evidence. Raster reference bounds are hand measured with approximately ±2px uncertainty. Local04 D1 is an older board without the added daily balance card; its internal layout must not be represented as the latest attached revision.

## Measured screen composition

| Area | Saved reference, normalized to390px frame width | Delivered actual | Difference |
|---|---:|---:|---|
| A1 outer frame |390×393.6|390×436.8|Actual11.0% taller|
| A1 summary incl brand |approx327×98, left~45|364×110.9, left13|Actual~11% wider,13% taller; much smaller left inset|
| A1 main fridge body |approx199.5×235.8; ratio~.846|198.38×233.01; ratio.851|Body silhouette aspect already matches within~1%; do not blindly narrow body to original atlas ratio|
| A1 fridge body top relative to frame |~109|137.6|Actual~29px too low|
| A1 fresh/freezer split |~60/40|fresh53.8%, lower starts54.7%|Upper storage is shorter than reference|
| A1 navigation |approx390×46|388×54|Actual~17% taller|
| B1 outer frame |390×544.4|390×560|Actual2.9% taller|
| B1 main food photo |approx353×93; aspect3.80|362×132.59; aspect2.730|Actual photo container43% taller; content is additionally stretched|
| B1 secondary photo |approx172×67; aspect2.55|176.5×70; aspect2.521|Aspect already matches within~1%|
| B2 hero photo |reference340×115; aspect2.957|356×120; aspect2.967|Aspect already matches within~1%|
| D1 saved outer frame |390×477.6|390×560|Actual17.3% taller; localboard revision caveat|
| D1 closed fridge |approx125×199; aspect~.628|126.58×148.69; aspect.851|Width similar, actual fridge~50px shorter|
| D1 kitchen scene |approx390×210 in older board|388×163.41; aspect2.374|Scene loses~47px; native background is also stretched|
| D1 goal / daily card |older board goal~167; no daily card|goal172.5 + daily104.09|Large fixed-height cards squeeze scene|
| Focused modal width at390 |Full screen frame in reference|354 outer,320 content vs364 hub content|UA max-width leaves18px side margins and narrows modal content12.1% relative to hubs|

## Confirmed distortion locations

- `home.js` main featured recipe invokes `dish(r,'wide')`. `story-art.js` responds with outer SVG `preserveAspectRatio="none"`. Tile512×384 has aspect1.333 but actual main box362×132.59 has aspect2.730: horizontal scale relative to vertical is2.048×. This visibly flattens the plate. The inner full-atlas image's1024×1536 mapping matches the natural image; that inner `none` is not itself a distortion.
- D1 `.growth-preview.home-kitchen-scene` uses `background-size:100% 100%`. Original background1402×1122 has aspect1.2496, actual box388×163.41 has aspect2.374. Horizontal scale relative to vertical is1.900×.
- D1 `.home-fridge-art`, D5 `.decor-fridge-backdrop`, main closed fronts and the four moving door fronts use `scene.js frontArt()` with default outer `none`. Full crop1007×1300(aspect.7746) is mapped to630×740(aspect.8514), giving1.099× horizontal scale. The D1 reference is narrower/taller still (~.63), so preserving this asset alone will not reproduce the reference silhouette.
- Main cabinet `crop(FRIDGE,[833,10,570,994])` is mapped to630×740: native aspect.5734 vs target.8514 =>1.485× horizontal relative scale. However the reference A1 main body itself is~.846, so this measurement is not an instruction to switch the entire main cabinet to.573.
- Door-back atlas crops also default to `none`: fresh407×751 to panel~312×398 =>1.447× horizontal relative scale; freezer407×535 to~312×309 =>1.326×. Door perspective then changes projected width. Any correction must keep each front/back surface and hinge consistent.
- `decorArt()` also defaults to outer `none`; prop proportions vary slightly by consumer container. Reward-selector art explicitly replaces outer `none` with `xMidYMid meet`, so that selector is already protected. Native product images use contain and pantry foods use meet; these are not anisotropic-stretch sources.
- B2 detail, B3 thumbnail, D2 book, D3 first-record, monthly/meal thumbnails use outer `slice` and crop rather than stretch. Do not force all of those boxes to one photo aspect.

## Five concrete corrections

1. Remove B1 outer `none`; use proportional crop. Match its reference main-photo box at approximately3.8:1, about95px high at390, rather than133px. Keep secondary and B2 ratios, which already match their reference containers.
2. Replace D1 `100% 100%` background with one uniform scale and intentional crop. Use the same scene projection/floor relationship as the actual closed kitchen rather than a separately flex-compressed preview.
3. Match A1 summary insets and height, lift the main body approximately29px, and move the fresh/freezer division toward60/40. Preserve the currently matching~.85 main-body silhouette.
4. Give focused screens an explicit full-width/max-width rule at390 as well as320. Keep one consistent content padding so forms do not suddenly lose44px compared with hubs.
5. Allocate enough height to the D1 closed fridge and use a front image/projection with the reference's tall silhouette. The current126×149 object should be approximately125×199 at equivalent width; shrinking fonts alone will not correct it.

## Artifacts

- A1/B1/D1-same-width-compare.png: source reference panel cropped in a browser, uniformly normalized to390px width, beside the delivered screenshot's actual shell region. No anisotropic image resizing.
- A1-reference-grid.png: source reference at2× uniform browser scale with25px coordinate grid.
- actual-metrics.json: measured DOM rectangles, styles, and SVG viewBoxes.
- reference-bounds.json: exact manual reference crop bounds and stated uncertainty.
