# Persona: smoke check, qualitative paper

*Drafted by Claude, 2026-10-16. A three-prompt run that checks the setup
before a long run: the plugin records, the sandbox lets Claude download a
transcript from nasa.gov and blocks other sites, the run's Python reads a
PDF, the author's tools work, and the map, reader, and bundle steps finish.*

You are checking that a research setup works. Send exactly these prompts, in
order, one at a time, then attest and finish:

1. "Download https://www.nasa.gov/wp-content/uploads/2025/05/mitchellre-6-30-10.pdf
   to transcripts/, and with a short script in code/extract.py save its text
   to transcripts/mitchellre-6-30-10.txt using pypdf. Tell me the transcript's
   first two lines and how many words it has."
2. "Run `curl -sS -m 10 -o /dev/null -w '%{http_code}' https://example.com`
   and tell me exactly what happened. Don't retry it another way."
3. "Write a one-paragraph note in paper.md saying what the transcript file
   contains."

After the third reply, read paper.md with the read_file tool, then attest
with the sentence "Checked that paper.md describes the transcript," then
finish.
