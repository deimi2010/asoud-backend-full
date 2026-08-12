\set ON_ERROR_STOP on
\pset pager off
\pset null '(null)'

-- Run only after snapshot_inventory.sql, and only on the isolated anonymized
-- snapshot. The output contains aggregate counts, never row identifiers,
-- authorities, account data, mobile numbers, or JSON payloads.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10min';
SET LOCAL lock_timeout = '5s';
SET LOCAL idle_in_transaction_session_timeout = '20min';

\echo '=== expected financial column types ==='
SELECT table_name,
       column_name,
       data_type,
       udt_name,
       numeric_precision,
       numeric_scale,
       is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
      'payment_payment',
      'payment_zarinpal',
      'wallet_wallet',
      'wallet_transaction',
      'order',
      'order_item',
      'gateway'
  )
ORDER BY table_name, ordinal_position;

SELECT (
    to_regclass('public.payment_payment') IS NOT NULL
    AND (
        SELECT count(*) = 8
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'payment_payment'
          AND column_name IN (
              'id', 'user_id', 'amount', 'status',
              'target_content_type_id', 'target_id',
              'gateway_content_type_id', 'gateway_id'
          )
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'payment_payment'
          AND column_name = 'amount'
          AND data_type IN ('real', 'double precision', 'numeric', 'decimal')
    )
) AS payment_shape_supported
\gset

\echo '=== payment anomalies ==='
\if :payment_shape_supported
SELECT count(*)::bigint AS total_rows,
       count(*) FILTER (WHERE amount IS NULL)::bigint AS null_amount_rows,
       count(*) FILTER (
           WHERE amount IS NOT NULL
             AND amount::text IN ('NaN', 'Infinity', '-Infinity')
       )::bigint AS non_finite_amount_rows,
       count(*) FILTER (
           WHERE amount IS NOT NULL
             AND amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND amount <= 0
       )::bigint AS non_positive_amount_rows,
       count(*) FILTER (
           WHERE amount IS NOT NULL
             AND amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND amount <> trunc(amount)
       )::bigint AS fractional_irt_rows,
       count(*) FILTER (
           WHERE amount IS NOT NULL
             AND amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND abs(amount) > 999999999999999999::numeric
       )::bigint AS outside_decimal_18_0_rows,
       count(*) FILTER (
           WHERE (target_content_type_id IS NULL) <> (target_id IS NULL)
       )::bigint AS partial_target_rows,
       count(*) FILTER (
           WHERE (gateway_content_type_id IS NULL) <> (gateway_id IS NULL)
       )::bigint AS partial_gateway_rows
FROM public.payment_payment;

SELECT status, count(*)::bigint AS row_count
FROM public.payment_payment
GROUP BY status
ORDER BY status;

SELECT count(*)::bigint AS duplicate_pending_target_groups,
       COALESCE(sum(group_size - 1), 0)::bigint AS duplicate_pending_extra_rows,
       COALESCE(max(group_size), 0)::bigint AS max_pending_group_size
FROM (
    SELECT count(*)::bigint AS group_size
    FROM public.payment_payment
    WHERE status = 'pending'
      AND target_content_type_id IS NOT NULL
      AND target_id IS NOT NULL
    GROUP BY user_id, target_content_type_id, target_id
    HAVING count(*) > 1
) duplicate_pending;
\else
\echo 'payment_payment is absent or structurally incompatible; stop payment data reconciliation and report its column inventory'
\endif

SELECT (
    to_regclass('public.payment_zarinpal') IS NOT NULL
    AND (
        SELECT count(*) = 5
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'payment_zarinpal'
          AND column_name IN ('id', 'payment_id', 'authority', 'transaction_id', 'verification_data')
    )
) AS zarinpal_shape_supported
\gset

\echo '=== Zarinpal relation/uniqueness anomalies ==='
\if :zarinpal_shape_supported
SELECT count(*) FILTER (WHERE payment_id IS NULL)::bigint AS rows_without_payment,
       count(*) FILTER (
           WHERE payment_id IS NOT NULL
             AND NOT EXISTS (
                 SELECT 1
                 FROM public.payment_payment p
                 WHERE p.id = payment_zarinpal.payment_id
             )
       )::bigint AS orphan_payment_rows
FROM public.payment_zarinpal;

SELECT count(*)::bigint AS duplicate_authority_groups,
       COALESCE(sum(group_size - 1), 0)::bigint AS duplicate_authority_extra_rows,
       COALESCE(max(group_size), 0)::bigint AS max_authority_group_size
FROM (
    SELECT count(*)::bigint AS group_size
    FROM public.payment_zarinpal
    WHERE authority IS NOT NULL AND authority <> ''
    GROUP BY authority
    HAVING count(*) > 1
) duplicate_authority;

SELECT count(*)::bigint AS duplicate_transaction_groups,
       COALESCE(sum(group_size - 1), 0)::bigint AS duplicate_transaction_extra_rows,
       COALESCE(max(group_size), 0)::bigint AS max_transaction_group_size
FROM (
    SELECT count(*)::bigint AS group_size
    FROM public.payment_zarinpal
    WHERE transaction_id IS NOT NULL AND transaction_id <> ''
    GROUP BY transaction_id
    HAVING count(*) > 1
) duplicate_transaction;

\if :payment_shape_supported
SELECT count(*) FILTER (
           WHERE p.status = 'completed'
             AND (z.transaction_id IS NULL OR z.transaction_id = '')
       )::bigint AS completed_without_transaction_id,
       count(*) FILTER (
           WHERE z.transaction_id IS NOT NULL
             AND z.transaction_id <> ''
             AND p.status <> 'completed'
       )::bigint AS transaction_id_on_non_completed_payment
FROM public.payment_zarinpal z
JOIN public.payment_payment p ON p.id = z.payment_id;
\endif
\else
\echo 'payment_zarinpal is absent or structurally incompatible; report its column inventory'
\endif

SELECT (
    to_regclass('public.wallet_wallet') IS NOT NULL
    AND (
        SELECT count(*) = 3
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'wallet_wallet'
          AND column_name IN ('id', 'user_id', 'balance')
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'wallet_wallet'
          AND column_name = 'balance'
          AND data_type IN ('real', 'double precision', 'numeric', 'decimal')
    )
) AS wallet_shape_supported
\gset

SELECT (
    to_regclass('public.wallet_transaction') IS NOT NULL
    AND (
        SELECT count(*) = 6
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'wallet_transaction'
          AND column_name IN ('id', 'user_id', 'from_wallet_id', 'to_wallet_id', 'action', 'amount')
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'wallet_transaction'
          AND column_name = 'amount'
          AND data_type IN ('real', 'double precision', 'numeric', 'decimal')
    )
) AS wallet_transaction_shape_supported
\gset

\echo '=== wallet anomalies ==='
\if :wallet_shape_supported
SELECT count(*)::bigint AS total_wallets,
       count(*) FILTER (WHERE balance::text IN ('NaN', 'Infinity', '-Infinity'))::bigint AS non_finite_balance_rows,
       count(*) FILTER (
           WHERE balance::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND balance < 0
       )::bigint AS negative_balance_rows,
       count(*) FILTER (
           WHERE balance::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND balance <> trunc(balance)
       )::bigint AS fractional_irt_balance_rows,
       count(*) FILTER (
           WHERE balance::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND abs(balance) > 999999999999999999::numeric
       )::bigint AS outside_decimal_18_0_balance_rows
FROM public.wallet_wallet;

SELECT count(*)::bigint AS duplicate_user_wallet_groups,
       COALESCE(sum(group_size - 1), 0)::bigint AS duplicate_user_wallet_extra_rows
FROM (
    SELECT count(*)::bigint AS group_size
    FROM public.wallet_wallet
    GROUP BY user_id
    HAVING count(*) > 1
) duplicate_wallets;
\else
\echo 'wallet_wallet is absent or structurally incompatible; stop wallet balance reconciliation and report its column inventory'
\endif

\if :wallet_transaction_shape_supported
SELECT count(*)::bigint AS total_transactions,
       count(*) FILTER (WHERE amount::text IN ('NaN', 'Infinity', '-Infinity'))::bigint AS non_finite_amount_rows,
       count(*) FILTER (
           WHERE amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND amount <= 0
       )::bigint AS non_positive_amount_rows,
       count(*) FILTER (
           WHERE amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND amount <> trunc(amount)
       )::bigint AS fractional_irt_rows,
       count(*) FILTER (
           WHERE amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
             AND abs(amount) > 999999999999999999::numeric
       )::bigint AS outside_decimal_18_0_rows,
       count(*) FILTER (WHERE action NOT IN ('charge', 'spend', 'exchange'))::bigint AS unknown_action_rows,
       count(*) FILTER (
           WHERE action IN ('charge', 'spend')
             AND from_wallet_id IS DISTINCT FROM to_wallet_id
       )::bigint AS local_action_wallet_mismatch_rows,
       count(*) FILTER (
           WHERE action = 'exchange'
             AND from_wallet_id IS NOT DISTINCT FROM to_wallet_id
       )::bigint AS self_exchange_rows
FROM public.wallet_transaction;

SELECT action, count(*)::bigint AS row_count
FROM public.wallet_transaction
GROUP BY action
ORDER BY action;

\if :wallet_shape_supported
SELECT count(*) FILTER (
           WHERE source.user_id IS DISTINCT FROM t.user_id
       )::bigint AS transaction_user_source_owner_mismatch_rows
FROM public.wallet_transaction t
JOIN public.wallet_wallet source ON source.id = t.from_wallet_id;

-- This is a discrepancy detector, not proof of corruption: production may
-- contain a legitimate opening balance predating the available ledger.
WITH reconstructed AS (
    SELECT w.id,
           CASE
               WHEN w.balance::text IN ('NaN', 'Infinity', '-Infinity') THEN NULL
               ELSE w.balance::numeric
           END AS stored_balance,
           COALESCE(sum(
               CASE
                   WHEN t.action = 'charge' AND t.from_wallet_id = w.id THEN t.amount::numeric
                   WHEN t.action = 'spend' AND t.from_wallet_id = w.id THEN -t.amount::numeric
                   WHEN t.action = 'exchange' AND t.from_wallet_id = w.id THEN -t.amount::numeric
                   WHEN t.action = 'exchange' AND t.to_wallet_id = w.id THEN t.amount::numeric
                   ELSE 0::numeric
               END
           ), 0::numeric) AS ledger_balance
    FROM public.wallet_wallet w
    LEFT JOIN public.wallet_transaction t
      ON t.from_wallet_id = w.id OR t.to_wallet_id = w.id
    WHERE t.amount IS NULL
       OR t.amount::text NOT IN ('NaN', 'Infinity', '-Infinity')
    GROUP BY w.id, w.balance
)
SELECT count(*) FILTER (
           WHERE stored_balance IS NOT NULL
             AND stored_balance <> ledger_balance
       )::bigint AS wallets_different_from_available_ledger,
       md5(
           count(*)::text || ':' ||
           COALESCE(sum(stored_balance), 0)::text || ':' ||
           COALESCE(sum(ledger_balance), 0)::text
       ) AS aggregate_reconciliation_fingerprint
FROM reconstructed;
\endif
\else
\echo 'wallet_transaction is absent or structurally incompatible; stop ledger reconciliation and report its column inventory'
\endif

SELECT (
    to_regclass('public.order') IS NOT NULL
    AND (
        SELECT count(*) = 9
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'order'
          AND column_name IN (
              'id', 'user_id', 'status', 'is_paid', 'inventory_status',
              'subtotal_amount', 'discount_amount', 'payable_amount',
              'discount_percentage_snapshot'
          )
    )
) AS order_shape_supported
\gset

SELECT (
    to_regclass('public.order_item') IS NOT NULL
    AND (
        SELECT count(*) = 6
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'order_item'
          AND column_name IN ('id', 'order_id', 'product_id', 'affiliate_id', 'quantity', 'unit_price')
    )
) AS order_item_shape_supported
\gset

\echo '=== order snapshot/inventory anomalies ==='
\if :order_shape_supported
SELECT status, is_paid, inventory_status, count(*)::bigint AS row_count
FROM public."order"
GROUP BY status, is_paid, inventory_status
ORDER BY status, is_paid, inventory_status;

SELECT count(*) FILTER (
           WHERE status <> 'draft'
             AND (subtotal_amount IS NULL OR payable_amount IS NULL)
       )::bigint AS placed_orders_without_frozen_totals,
       count(*) FILTER (
           WHERE subtotal_amount < 0 OR discount_amount < 0 OR payable_amount < 0
       )::bigint AS negative_snapshot_amount_rows,
       count(*) FILTER (
           WHERE payable_amount IS NOT NULL
             AND subtotal_amount IS NOT NULL
             AND payable_amount <> subtotal_amount - discount_amount
       )::bigint AS snapshot_arithmetic_mismatch_rows,
       count(*) FILTER (
           WHERE coalesce(subtotal_amount, 0) <> trunc(coalesce(subtotal_amount, 0))
              OR coalesce(discount_amount, 0) <> trunc(coalesce(discount_amount, 0))
              OR coalesce(payable_amount, 0) <> trunc(coalesce(payable_amount, 0))
       )::bigint AS fractional_irt_order_rows,
       count(*) FILTER (WHERE is_paid AND status <> 'completed')::bigint AS paid_non_completed_rows,
       count(*) FILTER (WHERE status = 'completed' AND NOT is_paid)::bigint AS completed_unpaid_rows,
       count(*) FILTER (
           WHERE discount_percentage_snapshot < 0 OR discount_percentage_snapshot > 100
       )::bigint AS invalid_discount_percentage_rows
FROM public."order";

SELECT count(*)::bigint AS duplicate_draft_user_groups,
       COALESCE(sum(group_size - 1), 0)::bigint AS duplicate_draft_extra_rows
FROM (
    SELECT count(*)::bigint AS group_size
    FROM public."order"
    WHERE status = 'draft'
    GROUP BY user_id
    HAVING count(*) > 1
) duplicate_drafts;
\else
\echo 'order is absent or does not have the current frozen-total shape; report its column inventory before designing any migration'
\endif

\if :order_item_shape_supported
SELECT count(*) FILTER (
           WHERE (product_id IS NULL) = (affiliate_id IS NULL)
       )::bigint AS rows_without_exactly_one_target,
       count(*) FILTER (WHERE quantity <= 0)::bigint AS non_positive_quantity_rows,
       count(*) FILTER (WHERE unit_price < 0)::bigint AS negative_unit_price_rows
FROM public.order_item;

\if :order_shape_supported
SELECT count(*) FILTER (
           WHERE o.status <> 'draft' AND i.unit_price IS NULL
       )::bigint AS placed_order_items_without_frozen_unit_price
FROM public.order_item i
JOIN public."order" o ON o.id = i.order_id;

WITH item_totals AS (
    SELECT order_id,
           sum(unit_price * quantity)::numeric AS calculated_subtotal
    FROM public.order_item
    WHERE unit_price IS NOT NULL
    GROUP BY order_id
)
SELECT count(*) FILTER (
           WHERE o.status <> 'draft'
             AND o.subtotal_amount IS NOT NULL
             AND totals.calculated_subtotal <> o.subtotal_amount
       )::bigint AS frozen_subtotal_item_mismatch_rows
FROM public."order" o
JOIN item_totals totals ON totals.order_id = o.id;
\endif
\else
\echo 'order_item is absent or structurally incompatible; report its column inventory'
\endif

SELECT (
    to_regclass('public.django_content_type') IS NOT NULL
    AND (
        SELECT count(*) = 3
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'django_content_type'
          AND column_name IN ('id', 'app_label', 'model')
    )
) AS content_type_shape_supported
\gset

\echo '=== payment/order cross-reconciliation ==='
\if :payment_shape_supported
\if :order_shape_supported
\if :content_type_shape_supported
WITH order_payments AS (
    SELECT p.id,
           p.target_id,
           p.status AS payment_status,
           CASE
               WHEN p.amount IS NULL OR p.amount::text IN ('NaN', 'Infinity', '-Infinity') THEN NULL
               ELSE p.amount::numeric
           END AS payment_amount
    FROM public.payment_payment p
    JOIN public.django_content_type ct ON ct.id = p.target_content_type_id
    WHERE ct.app_label = 'cart' AND ct.model = 'order'
)
SELECT count(*) FILTER (WHERE o.id IS NULL)::bigint AS payment_targets_missing_order,
       count(*) FILTER (
           WHERE o.id IS NOT NULL
             AND op.payment_amount IS NOT NULL
             AND o.payable_amount IS NOT NULL
             AND op.payment_amount <> o.payable_amount
       )::bigint AS payment_order_amount_mismatch_rows,
       count(*) FILTER (
           WHERE o.id IS NOT NULL
             AND op.payment_status = 'completed'
             AND NOT o.is_paid
       )::bigint AS completed_payment_for_unpaid_order_rows
FROM order_payments op
LEFT JOIN public."order" o ON o.id::text = op.target_id::text;

WITH completed_order_payments AS (
    SELECT p.target_id::text AS order_id, count(*)::bigint AS completed_count
    FROM public.payment_payment p
    JOIN public.django_content_type ct ON ct.id = p.target_content_type_id
    WHERE ct.app_label = 'cart'
      AND ct.model = 'order'
      AND p.status = 'completed'
    GROUP BY p.target_id::text
)
SELECT count(*) FILTER (
           WHERE o.is_paid AND coalesce(payments.completed_count, 0) = 0
       )::bigint AS paid_orders_without_completed_gateway_payment,
       count(*) FILTER (
           WHERE coalesce(payments.completed_count, 0) > 1
       )::bigint AS orders_with_multiple_completed_gateway_payments
FROM public."order" o
LEFT JOIN completed_order_payments payments ON payments.order_id = o.id::text;
\else
\echo 'django_content_type is absent or incompatible; skip generic payment target reconciliation'
\endif
\endif
\endif

SELECT (
    to_regclass('public.gateway') IS NOT NULL
    AND (
        SELECT count(*) = 6
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'gateway'
          AND column_name IN ('id', 'amount', 'status', 'invoice_number', 'reference_number', 'track_id')
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'gateway'
          AND column_name = 'amount'
          AND data_type IN ('real', 'double precision', 'numeric', 'decimal')
    )
) AS legacy_gateway_shape_supported
\gset

\echo '=== legacy gateway anomalies ==='
\if :legacy_gateway_shape_supported
SELECT count(*)::bigint AS total_rows,
       count(*) FILTER (WHERE amount::text IN ('NaN', 'Infinity', '-Infinity'))::bigint AS non_finite_amount_rows,
       count(*) FILTER (
           WHERE amount::text NOT IN ('NaN', 'Infinity', '-Infinity') AND amount <= 0
       )::bigint AS non_positive_amount_rows,
       count(*) FILTER (
           WHERE amount::text NOT IN ('NaN', 'Infinity', '-Infinity') AND amount <> trunc(amount)
       )::bigint AS fractional_irt_rows
FROM public.gateway;

SELECT status, count(*)::bigint AS row_count
FROM public.gateway
GROUP BY status
ORDER BY status;

SELECT count(*)::bigint AS duplicate_invoice_groups
FROM (
    SELECT invoice_number
    FROM public.gateway
    WHERE invoice_number IS NOT NULL AND invoice_number <> ''
    GROUP BY invoice_number
    HAVING count(*) > 1
) duplicate_invoices;

SELECT count(*)::bigint AS duplicate_reference_groups
FROM (
    SELECT reference_number
    FROM public.gateway
    WHERE reference_number IS NOT NULL AND reference_number <> ''
    GROUP BY reference_number
    HAVING count(*) > 1
) duplicate_references;

SELECT count(*)::bigint AS duplicate_track_id_groups
FROM (
    SELECT track_id
    FROM public.gateway
    WHERE track_id IS NOT NULL AND track_id <> ''
    GROUP BY track_id
    HAVING count(*) > 1
) duplicate_tracks;
\else
\echo 'legacy gateway is absent or structurally incompatible; report its column inventory'
\endif

ROLLBACK;
