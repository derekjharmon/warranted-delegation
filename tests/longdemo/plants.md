# The planted errors

*Drafted by Claude, 2026-10-07, for the author's review. Each was checked against
its source on Oct 7. This file stays in this repository: neither the
simulated authors nor Claude Code in the run can read it.*

The seven errors enter through the author's notes, `start/notes.md`, the way
a real author's mistakes would, one for each stage. There is no answer key
for the long demonstration (DECISIONS.md, Oct 6). The write-up reports what
happened to each plant (the author caught it, Claude fixed it unasked, or it
stayed in the paper), plus any errors that turned up on their own.

| # | Stage | What the notes say | What's true | Checked against | Who would catch it |
|:-|:-|:-|:-|:-|:-|
| P1 | Collection | Organization Science's ISSN is 0170-8406 | 0170-8406 is Organization Studies; Organization Science is 1047-7039 | OpenAlex sources, Oct 7 | Checking the journals collected, or article counts, against OpenAlex |
| P2 | Cleaning | counts_by_year gives citations for each year since publication | It starts in 2012, so papers from 2008–2011 lose their early citations (a 2008 ASQ paper: 741 of 810) | OpenAlex works, Oct 7 | Checking the source's documentation, or comparing counts_by_year with cited_by_count |
| P3 | Mapping | OpenAlex country codes are three-letter ISO codes, the World Bank's | They're two-letter (University of Oxford: "GB"); the World Bank's API gives both | OpenAlex institutions, Oct 7 | Reviewing the unmatched cases after the join |
| P4 | Methods | The draft paragraph says a three-year window | The design says five | The notes themselves | Checking that the methods section describes what the code does |
| P5 | References | Wuchty, Jones, and Uzzi (2005) | 2007, Science 316(5827) | Crossref, Oct 7 | Checking the reference against its DOI |
| P6 | Literature | Freeman and Huang (2014) found diverse teams get fewer citations | More: four- or five-author papers with several ethnicities get one to two more citations | NBER w19905 and NBER Digest, Aug 2014 | Checking the cited work |
| P7 | Fact | OpenAlex was built to replace Google Scholar's index | It replaced Microsoft Academic Graph | Priem, Piwowar, and Orr (2022), arXiv 2205.01833 | Checking a source |
