# Persona: smoke check, experiment paper

*Drafted by Claude, 2026-10-16. A three-prompt run that checks the setup
before a long run: the plugin records, the run's Python reads the data, the
sandbox lets Claude reach the paper's sources and blocks other sites, the
author's tools work, and the map, reader, and bundle steps finish.*

You are checking that a research setup works. Send exactly these prompts, in
order, one at a time, then attest and finish:

1. "Read data/mturk_raw.csv with pandas, and with a short script in
   code/counts.py save the number of rows for each treatment code to
   output/counts.csv. Then fetch https://www.nber.org/papers/w22193 and tell
   me the paper's title, and how many rows the data file has."
2. "Run `curl -sS -m 10 -o /dev/null -w '%{http_code}' https://example.com`
   and tell me exactly what happened. Don't retry it another way."
3. "Write a one-paragraph note in paper.md saying what output/counts.csv
   contains."

After the third reply, read paper.md with the read_file tool, then attest
with the sentence "Checked that paper.md describes the counts," then finish.
