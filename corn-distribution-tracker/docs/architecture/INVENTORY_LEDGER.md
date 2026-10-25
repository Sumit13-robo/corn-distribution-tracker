# Inventory Ledger Rules and Metric Definitions

## Ledger semantics
- Receipt: add quantity to central account (source is external/nullable, destination central).
- Allocation: transfer from central to a distributor account.
- Approved distribution: transfer from distributor account to assigned site account, referencing exactly one approved distribution record.
- Return: transfer from site/distributor account back to a destination account.
- Loss/spoilage: remove from source account only with admin permission, required reason, and audit event.
- Adjustment: use a controlled reconciliation workflow. Prefer paired transfer/reversal entries; never edit old posted entries. Require reason, admin identity, and—where practical—second-person approval for high-value adjustments.
- Reversal: a new compensating movement that references the original; never delete the original.

For every transfer, debit/source and credit/destination are represented by one movement row. For each posted movement, exactly one source loses and one destination gains the same quantity. A loss/adjustment uses documented sink/source semantics. All APIs execute under a database transaction and prevent races through row locks or serializable/advisory protection as appropriate.

## Pending reservation
`reserved_kg(account) = sum(quantity_kg)` for valid `SUBMITTED` delivery records owned by the distributor account and not approved/rejected/cancelled. `available_kg = posted_balance_kg - reserved_kg`. On submit, lock the relevant distributor account/assignment or use an atomic reservation table and validate the aggregate before committing. Two simultaneous submissions must not reserve the same last kilogram twice.

## Metric definitions
- **Received**: sum of posted receipt movements into central stock for selected filters/time window.
- **Central on hand**: posted central account balance.
- **Distributor-held**: sum of posted balances for distributor accounts.
- **Site stock / approved distributed**: posted balances at site accounts or sum of approved delivery movements for the campaign/window. Label whether the metric is a current balance or period flow.
- **Submitted pending**: sum of quantities in SUBMITTED state. Not counted as verified delivery.
- **Approved delivered (period)**: sum of delivery movements posted for approved records in the selected period.
- **Target**: sum of active assignment targets in the selected campaign/filter context.
- **Remaining target**: `max(target_kg - approved_delivered_for_target_kg, 0)` per assignment, aggregated after applying assignment boundaries. Report overage separately instead of hiding it.
- **Rejected**: sum of quantities in REJECTED state during the selected submission window; this is not stock distributed.
- **Unallocated central stock**: central on hand less amounts reserved for transfers, if transfer requests are pending; do not use a negative value.
- **Variance**: show the chosen comparison explicitly, e.g. `approved delivery - target` or `received - current known balances - recorded losses`. Do not label ambiguous math “variance”.
- **Evidence completeness**: approved submissions with required valid evidence / all approved submissions. Flagged evidence is visible separately; policy must define whether accepted exceptions count as complete.

## Units
Database stores kg. Conversions: 1 quintal = 100 kg; 1 metric tonne = 1000 kg. Bag conversion = configured `kg_per_bag` value for the selected campaign/organization; display the configured conversion near the field and report. Convert input to kg in a decimal-safe service. Define and test rounding/precision for UI display; never round stored data before ledger posting.

## Corrections and idempotency
- Each stock-posting mutation (receipt, allocation, adjustment and delivery approval) accepts an idempotency key; persist it under a unique constraint and return the original result on retry. Reject/cancel actions are state transitions, not stock postings, and do not require a key.
- A posted movement has a unique relationship to its business source (e.g., one movement per approved distribution record).
- Duplicate approval calls return the current approved record and do not post another movement.
- If an approved delivery was incorrect, the admin uses a reversal/adjustment flow with reason. The historical delivery/evidence remains visible.
