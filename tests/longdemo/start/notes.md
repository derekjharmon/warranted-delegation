# Notes: team composition and citations in management research

## The idea

Do management papers written by larger teams, and by teams spread across
countries, get cited more? Team science is now the norm in most fields, and
management has followed: single-authored papers in our top journals are
becoming rare. If team papers are cited more, is that about size (more
people, more networks to spread the paper) or about reach (coauthors in
different countries bring different audiences)?

Two hypotheses, roughly:

- H1: Papers with more authors receive more citations.
- H2: Papers whose authors are based in more than one country receive more
  citations, beyond what team size alone explains.

A possible extension: whether it matters that a team includes an author
from a country outside the World Bank's high-income group.

## Data

OpenAlex, which has a free API. It was built to replace Google Scholar's
index after Google closed it to bulk access by researchers, so coverage of
journals should be good.

Journals and ISSNs:

- Administrative Science Quarterly: 0001-8392
- Academy of Management Journal: 0001-4273
- Strategic Management Journal: 0143-2095
- Organization Science: 0170-8406

Years: 2008 to 2017, so every paper has at least five years of citations.

Citations: count the citations each paper received in its first five years.
OpenAlex's counts_by_year field gives citations for each year since a paper
was published, so the window can be built from it directly.

Countries: OpenAlex gives each institution a three-letter ISO country code
(USA, GBR, DEU), the same codes the World Bank uses, so joining to the World
Bank's income groups should be direct.

## Draft methods paragraph (from an earlier version)

We count the citations each article received in the three years after
publication. We estimate negative binomial models of citations on the number
of authors and on whether the authors' institutions span more than one
country, with journal and year fixed effects.

## Literature

- Wuchty, Jones, and Uzzi (2005): teams increasingly dominate the production
  of knowledge across fields, and team papers are cited more than solo papers.
- Freeman and Huang (2014): papers by ethnically diverse author teams receive
  fewer citations than papers by teams of the same ethnicity.
- Larivière, Gingras, Sugimoto, and Tsou (2015): the relationship between
  team size and citation impact over the twentieth century.

## References

Freeman, R. B., & Huang, W. (2014). Collaboration: Strength in diversity.
Nature, 513(7518), 305.

Larivière, V., Gingras, Y., Sugimoto, C. R., & Tsou, A. (2015). Team size
matters: Collaboration and scientific impact since 1900. Journal of the
Association for Information Science and Technology, 66(7), 1323–1332.

Wuchty, S., Jones, B. F., & Uzzi, B. (2005). The increasing dominance of
teams in production of knowledge. Science, 316(5827), 1036–1039.
