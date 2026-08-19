# Real Estate Terminology

This project-maintained glossary provides concise definitions of real estate
terms used by the IDX Exchange knowledge RAG assistant.

Definitions are based on the external sources listed in each section.
Project-specific usage is identified separately where applicable.

This document is not official IDX Exchange documentation.

Last reviewed: August 2026

---

## DOM — Days on Market

Days on Market (DOM) generally refers to the amount of time a property remains
listed for sale before it is taken off the market.

Freddie Mac defines days on market as the time between when a home is listed
for sale and when it is taken off the market. Average DOM can also provide
information about market conditions: lower average DOM can indicate stronger
buyer competition, while higher average DOM can indicate weaker competition.

Exact DOM calculation rules can vary across MLS systems, particularly when a
listing is withdrawn, relisted, or otherwise changes status.

In this project, the `DaysOnMarket` field is used in sold-comparable retrieval
and market-analysis workflows.

Sources:
- Freddie Mac, "Why Days on Market Matters When Selling Your Home"
- IDX Exchange project-maintained MLS field mapping for project-specific usage

---

## Escrow

Escrow is a process used in real estate transfers and financing in which
documents, funds, or other items of value are deposited with a neutral and
disinterested third party, known as the escrow agent.

The escrow agent holds these items until specified events or conditions occur
according to written instructions agreed to by the parties.

California Department of Real Estate describes escrow as a commonly used
process for buying, selling, and refinancing real estate in California.

Source:
- California Department of Real Estate,
  "Surviving the Real Estate Escrow Process in California"

---

## Comparable Sales — Comps

Comparable sales, commonly called comps, are properties used as points of
comparison when analyzing the value of a subject property.

Fannie Mae guidance states that comparable sales should have relevant physical,
legal, and market characteristics in common with the subject property.
Characteristics considered in comparable selection can include location, site,
room count, finished area, style, condition, and other factors affecting value.

Comparable properties do not need to be identical to the subject property,
but they should provide meaningful evidence for comparison.

In this project, historical transactions from `california_sold` are used for
sold-comparable retrieval and market analysis.

Sources:
- Fannie Mae Selling Guide, B4-1.3-08, "Comparable Sales"
- IDX Exchange project-maintained MLS field mapping for project-specific usage

---

## Sales Comparison Approach

The sales comparison approach estimates property value by analyzing sales,
contract sales, and listings of properties that are comparable to the subject
property.

The analysis considers relevant similarities and differences between the
subject and comparable properties that may affect value.

Source:
- Fannie Mae Selling Guide, B4-1.3-07,
  "Sales Comparison Approach Section of the Appraisal Report"

---

## Capitalization Rate — Cap Rate

A capitalization rate, commonly called a cap rate, is a rate used in
income-property valuation to relate a property's net operating income to its
value.

A common direct-capitalization relationship is:

`Property Value = Net Operating Income / Capitalization Rate`

or:

`V = I / R`

Rearranging the relationship gives:

`Capitalization Rate = Net Operating Income / Property Value`

or:

`R = I / V`

The capitalization rate therefore represents the rate used to convert an
income stream into an indication of property value.

Sources:
- California Department of Real Estate, Reference Book, Chapter 27, "Glossary"
- California Department of Real Estate, Reference Book, Chapter 15,
  "Appraisal and Valuation"

---

## Net Operating Income — NOI

Net Operating Income (NOI) is the income attributable to an income-producing
property after applicable operating expenses are deducted, before considering
items such as financing costs.

NOI is used in income-property valuation and is the income component of the
direct-capitalization relationship:

`Property Value = NOI / Capitalization Rate`

Source:
- California Department of Real Estate, Reference Book, Chapter 15,
  "Appraisal and Valuation"

---

## List-to-Close Price Ratio

The list-to-close price ratio compares a property's final sale or closing price
with its listing price.

A general representation is:

`Sale Price / List Price * 100`

A value above 100% indicates that the sale price was above the referenced list
price, while a value below 100% indicates that the sale price was below the
referenced list price.

The exact interpretation depends on which listing price is used, such as the
original list price or the most recent list price.

In the IDX Exchange internship handbook's Week 5 market-analysis example, the
project metric is calculated as:

`ClosePrice / ListPrice * 100`

and is described as a negotiation-leverage indicator.

Sources:
- National Association of REALTORS, home-sales reporting using sale/list-price
  comparisons
- IDX Exchange Agentic AI Engineer Intern Handbook, Week 5,
  for the project-specific formula and interpretation

---

## References

1. Freddie Mac — Why Days on Market Matters When Selling Your Home
   https://myhome.freddiemac.com/blog/selling/why-days-market-matters-when-selling-your-home

2. California Department of Real Estate — Surviving the Real Estate Escrow
   Process in California
   https://www.dre.ca.gov/files/pdf/re23.pdf

3. California Department of Real Estate — Reference Book, Chapter 27: Glossary
   https://www.dre.ca.gov/files/pdf/refbook/ref27.pdf

4. California Department of Real Estate — Reference Book, Chapter 15:
   Appraisal and Valuation
   https://www.dre.ca.gov/files/pdf/refbook/ref15.pdf

5. Fannie Mae Selling Guide — B4-1.3-08, Comparable Sales
   https://selling-guide.fanniemae.com/sel/b4-1.3-08/comparable-sales

6. Fannie Mae Selling Guide — B4-1.3-07,
   Sales Comparison Approach Section of the Appraisal Report
   https://selling-guide.fanniemae.com/sel/b4-1.3-07/sales-comparison-approach-section-appraisal-report

7. National Association of REALTORS — Home-sales reporting and
   sale-to-list-price comparisons
   https://www.nar.realtor/

8. IDX Exchange Agentic AI Engineer Intern Handbook, Week 5
   Local internship-provided source; not included in the public repository.