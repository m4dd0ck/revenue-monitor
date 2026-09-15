-- MRR reads the first subscription item only. Fail loudly if a multi-item subscription appears
-- (possible with real Stripe data) rather than silently undercount it.
select subscription_version_id, subscription_id, item_count
from {{ ref('dim_subscription_history') }}
where item_count != 1
