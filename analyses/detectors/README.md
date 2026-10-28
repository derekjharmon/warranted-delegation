# AI-text detectors (Appendix A7)

Two commercial detectors, Pangram (model 4.1) and GPTZero (model of 2026-10-07), scored the body text of sixteen documents on October 19, 2026: the twelve demonstration papers, and four versions of one published, single-authored management journal article whose accepted manuscript predates ChatGPT (the accepted manuscript, the journal's copy edit, and two copy edits by Claude).

    python3 detect.py table      the results, as a table, from the saved responses

`results/<detector>/` keeps each detector's response with the text taken out. For the published article, this copy keeps only each detector's verdict and scores, under neutral names (`article-*.json`), without the journal, dates, word counts, or the text's fingerprint, since any of them could identify its author. The texts themselves are not here, so `detect.py texts` and `detect.py run` don't work in this copy, and the share of words each copy edit changed (A7) can't be checked from it.
