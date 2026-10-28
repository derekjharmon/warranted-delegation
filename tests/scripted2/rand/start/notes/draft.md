# Draft paragraphs

*Written before I wrote the plan.*

## Background

When people pay part of the cost of their care, do they use less of it? The
RAND Health Insurance Experiment answered this by assigning families at
random to insurance plans that differed in how much of the bill they paid.
Aron-Dine, Einav, and Finkelstein (2013) revisit the experiment and conclude
that cost sharing had no effect on how often people saw a doctor. Deb and
Trivedi (2002) use the same data to model the demand for doctor visits.

## Data

The experiment ran in a single city, Seattle. The data, as distributed by
Cameron and Trivedi (2005), have one row per person-year, with the number of
outpatient doctor visits, the plan's coinsurance rate, whether the plan had
an individual deductible, and measures of health. Across person-years, the
average is 3.9 outpatient visits.

## Methods

We estimate the number of visits with a linear regression by OLS.
