# 2026 US midterm election results — by party

Results of the November 3, 2026 midterm elections, gathered to colour the
cartogram pages by winning party (governors, Senate, House).

## As-of

- **Snapshot: Sunday, November 8, 2026, ~16:30 PT / Monday, November 9, 2026, ~00:30 UTC.**
- Election Day was Tuesday, November 3, 2026. Results are **unofficial**;
  states certify in the coming weeks. Race "calls" are projections by news
  organisations (mostly the AP), not official results.
- Wikipedia revisions actually read (MediaWiki API, saved in `raw/`):
  - Governors: `2026_United_States_gubernatorial_elections`,
    rev 2026-11-09T00:23:26Z
  - Senate: `2026_United_States_Senate_elections`, rev 2026-11-08T22:37:19Z
  - House: `2026_United_States_House_of_Representatives_elections`,
    rev 2026-11-08T22:59:22Z
- Vote shares for House races come from Daily Letter race pages, which
  republish Associated Press data; those pages were last updated Nov 4–6 ET,
  so House percentages are a Nov 5–6 snapshot, while winners/calls are as of
  the Wikipedia revisions above (Nov 8 evening). Senate percentages come from
  the Wikipedia state-section infoboxes (same Nov 8 revisions).
  Governor percentages come from the Wikipedia race-summary table (sourced
  there to the New York Times governor results page).

## Files

- `governors_2026.csv` — 36 rows (one per state with a 2026 governor race).
- `senate_2026.csv` — 35 rows (33 Class 2 regular + 2 Class 3 specials).
- `house_2026.csv` — 435 rows (one per voting district).
- `raw/` — source snapshots: Wikipedia wikitext JSON + `.wiki` extracts,
  AP/Daily Letter HTML, fetch/parse scripts (`parse_gov.py`,
  `parse_senate_wiki.py`, `parse_senate_infobox.py`, `parse_house_wiki.py`,
  `parse_dl_house.py`, `parse_house_dl_races.py`, `build_house.py`).

## Column conventions

- `winner_party`: D / R / I / other. Minnesota DFL is coded D (the DFL is
  Minnesota's Democratic affiliate).
- `called` = `yes` means a news organisation has called the race for the
  named winner. `called` = `no` means **no winner yet**: `winner_name` and
  `winner_party` are blank, but `winner_pct` / `runnerup_pct` / `margin_pts`
  are filled with the **current leader's / trailer's share of the counted
  vote** (partial count), so a map can still show the state of play. Never
  read those percentages as final.
- `district_code` in `house_2026.csv` is the Census geoid (`state FIPS` +
  zero-padded district number; at-large districts use `00`, e.g. AK `0200`,
  DE `1000`). All 435 codes were verified against `../districts.csv`
  (voting districts only; the 6 non-voting delegates are excluded).
- `seat_class` in `senate_2026.csv` is `2` (regular, term to Jan 2033) or
  `3 special` (term to Jan 2029).

## Tallies (as of this snapshot)

### Governors — 36 races, 34 called, 2 uncalled

- Called: **D 22, R 12**. Uncalled: Alaska, Kansas (both D-leading).
- Democratic flips called (5): Georgia (Bottoms), Iowa (Sand), Nevada
  (Ford), Ohio (Acton), Texas (Hinojosa). Alaska would be a 6th flip if the
  D lead holds.
- Overall: Democrats won a majority of governorships for the first time
  since 2009. Before: R 26 / D 24. After (called only): D 28 / R 20, with
  Alaska (R-held) and Kansas (D-held) pending — range D 28–30 / R 20–22.
- States with **no** 2026 governor race (14): Delaware, Indiana, Kentucky,
  Louisiana, Mississippi, Missouri, Montana, New Jersey, North Carolina,
  North Dakota, Utah, Virginia, Washington, West Virginia.
- Note: MultiState's Nov 5 summary called Alaska a Democratic flip; the AP
  and Wikipedia both still list Alaska uncalled as of Nov 8, so it stays
  uncalled here.

### Senate — 35 seats up, 33 called, 2 uncalled

- Called: **D 20, R 13**. Uncalled: Alaska, Mississippi (both R-held).
- Democratic flips (7): Iowa (Turek), Kansas (Hamilton), Maine (Jackson),
  North Carolina (Cooper), Ohio special (Brown), South Carolina (Andrews),
  Texas (Talarico). No Republican flips. No Democratic-held seat up was lost.
- Special elections: Florida Class 3 (Moody R re-elected, 50.9–48.0 over
  Nixon — the closest called Senate race) and Ohio Class 3 (Brown D beat
  appointed incumbent Husted 50.0–45.2). Both serve to January 2029; the
  other 33 seats serve to January 2033.
- Composition after (called only): D 54 / R 44, with Alaska and Mississippi
  pending. Before: R 53 / D 47 (incl. 2 independents caucusing with D).

### House — 435 seats, 416 called, 19 uncalled

- Called: **D 254, R 162**. Uncalled: 19 (listed below).
- Democrats won control of the House. Before: R 218 / D 214, 1 independent
  caucusing with R, 2 vacancies. As of Nov 6, Ballotpedia counted 45 seats
  changing party control (43 to D, 2 to R); the only Republican flips were
  TN-09 (Brent Taylor, +1.1) and TX-32 (Jace Yarbrough, +3.0).
- House popular vote (Wikipedia infobox, as of Nov 6, 11:15 PM ET):
  D 63,622,014 (55.73%), R 48,873,294 (42.80%) — the largest Democratic
  House popular-vote margin since 1976 per that page.
- Closest called House races: TN-04 (Broderick D, +0.2 — but the AP had
  not called it; see note 2), FL-09 (Soto D, +0.6, same caveat), FL-13
  (Luna R, +0.8), SC-01 (Lacore D, +1.0), TN-09 (Taylor R, +1.1).

## Uncalled races (as of this snapshot)

### Governors (2)

| State | Leader (party) | Leader share | Trailer share | Margin | Note |
|---|---|---|---|---|---|
| Alaska | Jonathan Kreiss-Tomkins (D) | 49.1% | Bernadette Wilson (R) 29.2% | 19.9 | Ranked-choice; shares are first-choice, final tabulation pending. AP: too early to call, ~74% in. |
| Kansas | Cindy Holscher (D) | 50.3% | Ty Masterson (R) 49.7% | 0.6 | ~99% in. Closest governor race. |

### Senate (2)

| State | Note |
|---|---|
| Alaska | Ranked-choice; no vote shares published in the source yet. Peltola (D) vs Sullivan (R, incumbent). Media reports favour the Democrat. |
| Mississippi | No vote shares published in the source yet. Hyde-Smith (R, incumbent) vs Colom (D). |

### House (19)

Leaders and margins are from AP data via Daily Letter (Nov 5–6 snapshot;
`% counted` is the AP estimated-vote figure from the same source).

| District | Leader (party) | Margin | Counted | Note |
|---|---|---|---|---|
| AK-AL | Nick Begich (R) | +9.2 | 74% | Ranked-choice, first-choice shares 49.6 / 40.4. |
| AZ-02 | Eli Crane (R) | +1.0 | 97% | |
| CA-04 | Eric Jones (D) | +2.8 | 54% | Two Democrats; party outcome D either way. |
| CA-07 | Doris Matsui (D) | +11.4 | 67% | Slow California count. |
| CA-23 | Jay Obernolte (R) | +2.4 | 68% | Slow California count. |
| CA-40 | Ken Calvert (R) | +7.8 | 63% | Slow California count. |
| CO-04 | Eileen Laubacher (D) | +0.9 | 97% | |
| FL-07 | Ryan Elijah (R) | +0.5 | 99% | Recount territory. |
| FL-26 | Mario Diaz-Balart (R) | +0.8 | 99% | Recount territory. |
| FL-27 | Maria Elvira Salazar (R) | +0.4 | 99% | Recount territory. |
| LA-05 | Patricia Moore (D) | +0.7 | 99% | Jungle primary: **runoff Dec 12** vs Gabe Firment (R). First round 17.9 / 17.2. |
| LA-06 | Chauna Banks (D) | +0.2 | 99% | Jungle primary: **runoff Dec 12** vs Blake Miguez (R). First round 19.4 / 19.2. |
| MN-01 | Jake Johnson (D) | +0.0 | 99% | Effectively tied. |
| NC-03 | Greg Murphy (R) | +0.1 | 99% | Effectively tied. |
| NC-05 | Chuck Hubbard (D) | +0.0 | 99% | Effectively tied. |
| NC-07 | David Rouzer (R) | +0.8 | 99% | |
| NC-10 | Pat Harrigan (R) | +1.0 | 99% | |
| SC-02 | Joe Wilson (R) | +1.0 | 99% | |
| WA-05 | Michael Baumgartner (R) | +3.6 | 81% | |

If all 19 leaders held, the House would finish D 261 / R 174 (leaders split
D 7 / R 12). California, Florida and North Carolina account for 10 of the 19.

## What is shaky — read before building on this

1. **Calls differ by caller and by the hour.** Wikipedia (Nov 8, 22:59 UTC)
   had called 415 House races; the AP tally at the same time had 413; DDHQ
   via Poliwave had 418. The CSV follows Wikipedia as primary, with one
   exception: OK-03 is marked called for Frank Lucas (R, 64.0–36.0) on the
   AP call, which Wikipedia's revision had not yet recorded.
2. **Three House races Wikipedia calls but the AP had not (as of Nov 6
   data):** FL-09 (Soto D, +0.6 at 99% — genuine recount risk), ME-02
   (LePage R, +1.6), TN-04 (Broderick D, +0.2 at 99% — genuine recount
   risk). CA-14 (Wahab D, +13.0) is the same pattern but a wide margin.
   Treat FL-09 and TN-04 as liable to flip on recount/certification.
3. **Louisiana runoffs decide 2 House seats on December 12, 2026**
   (LA-05: Moore D vs Firment R; LA-06: Banks D vs Miguez R).
4. **Alaska is ranked-choice everywhere:** governor (first-choice shares
   only), Senate and House at-large (no final-round tabulation yet).
   First-choice shares are not final margins.
5. **California counts slowly.** Four House races uncalled there are mostly
   mail-ballot backlog, not close races (CA-07 is +11.4).
6. **House percentages are a Nov 5–6 snapshot** (Daily Letter / AP page
   timestamps), while winners/calls are Nov 8. Shares for called races may
   have moved a point or so since; winners will not have.
7. **FL-10 (Frost, D, called) has no vote shares in any source consulted**
   — the AP called it at poll close with 0% counted and published no
   totals. Its percentage fields are blank, the only such called race.
8. **ME-02** lists 1.8% "Blank Votes" as a third finisher in the AP data —
   Maine counts blank ballots in the total.
9. **Tennessee governor** was called for Blackburn (R) on a 45.5% plurality
   in a multi-candidate field (Green D 43.0%).
10. **Minnesota** candidates run as DFL (Democratic–Farmer–Labor); coded D.
11. The Wikipedia House page's own "seats won" (D 254 / R 162) matches this
    file's called tally exactly; the governors infobox (D 22 / R 12 won) and
    Senate counts (D 20 / R 13) also match. The AP's live tally differed by
    2–3 seats in each chamber at the same hour — that is caller lag, not an
    error in either source.

## Sources consulted

- Wikipedia, "2026 United States gubernatorial elections" —
  https://en.wikipedia.org/wiki/2026_United_States_gubernatorial_elections
- Wikipedia, "2026 United States Senate elections" —
  https://en.wikipedia.org/wiki/2026_United_States_Senate_elections
- Wikipedia, "2026 United States House of Representatives elections" —
  https://en.wikipedia.org/wiki/2026_United_States_House_of_Representatives_elections
- Wikipedia, "2026 United States elections" (overview / cross-check) —
  https://en.wikipedia.org/wiki/2026_United_States_elections
- Associated Press election results (governors, Senate, House) —
  https://apnews.com/projects/elections-2026/ (call status and House
  balance of power; accessed via search index, Nov 8–9)
- Daily Letter, 2026 midterms hub and per-race pages (AP data republished) —
  https://dailyletter.us/midterms-2026/house and
  https://dailyletter.us/midterms-2026/race/… (435 House race pages)
- Ballotpedia, "Election results, 2026" (cross-check on flips and totals) —
  https://ballotpedia.org/Election_results,_2026
- MultiState, "Governors | 2026 State Election Results" (governor flips and
  no-race states) —
  https://www.multistate.us/resources/governors-2026-state-election-results
- Shreveport Times / Louisiana First News (Louisiana Dec 12 runoffs) —
  https://www.shreveporttimes.com/story/news/election/2026/11/05/when-is-the-runoff-for-the-representative-election-in-louisiana-which-districts-candidates/92624627007/
- U.S. Census Bureau, 2024 Cartographic Boundary Files / 2020 Census P1
  (`../districts.csv`) — district codes only, not results.
