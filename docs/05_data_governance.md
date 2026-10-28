# Data Governance and PII

## PII policy
Columns that could identify a person (email, phone, full name, address, IP address, user or
customer IDs) must be classified before a table is shared outside the data team.
The assistant scans column names and sample values and labels each column `pii` or `none`.

## Current status
The crypto pipeline stores market data only — prices, volumes, coin names and symbols — so no
column is expected to contain personal data. Any column flagged `pii` is a red flag and must be
reviewed before the next release.

## Ownership
Every layer is owned by the data engineering team. Platinum tables are read by the analytics
dashboard; changes to their schema must be announced a day in advance.
