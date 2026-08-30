ALTER TABLE close_gap_reconciliations
  DROP CONSTRAINT IF EXISTS close_gap_reconciliations_status_check;

ALTER TABLE close_gap_reconciliations
  ADD CONSTRAINT close_gap_reconciliations_status_check
  CHECK (status IN (
    'SUSPENSION_CONFIRMED',
    'SUSPENSION_ASSUMED',
    'UNEXPLAINED_MISSING',
    'STATUS_UNKNOWN',
    'QUARANTINED'
  ));
