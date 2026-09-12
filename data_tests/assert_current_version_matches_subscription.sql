-- Replaying events must land on the subscription's current state.
select history.subscription_id
from {{ ref('dim_subscription_history') }} as history
inner join {{ ref('stg_stripe__subscriptions') }} as current_state using (subscription_id)
where history.is_current
  and (
      history.status != current_state.status
      or history.price_id != current_state.price_id
      or history.quantity != current_state.quantity
  )
