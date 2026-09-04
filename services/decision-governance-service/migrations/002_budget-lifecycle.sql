-- 扩展预算预留生命周期；仅允许 RESERVED/DISPATCHING 释放，CONSUMED 永久占用当日批次。
ALTER TABLE decision_budget_reservations DROP CONSTRAINT IF EXISTS decision_budget_reservations_status_check;
ALTER TABLE decision_budget_reservations ADD CONSTRAINT decision_budget_reservations_status_check CHECK (status IN ('RESERVED', 'DISPATCHING', 'CONSUMED', 'RELEASED'));
