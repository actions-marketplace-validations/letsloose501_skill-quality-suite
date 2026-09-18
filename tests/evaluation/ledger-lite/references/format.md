# Ledger format

## Columns

`date,amount,counterparty` - the date ISO-8601, the amount in minor units, the
counterparty as written.

## Rounding

Amounts are stored in minor units, so nothing is rounded on the way in. The balance is
printed with two decimals.
