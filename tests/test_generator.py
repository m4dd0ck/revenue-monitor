from collections import Counter
from collections.abc import Callable
from typing import Any

from conftest import RawData

from revenue_monitor.models import MODEL_BY_OBJECT


def items_of(snapshot: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = snapshot["items"]["data"][0]
    return item


class TestDeterminism:
    def test_same_seed_produces_identical_output(
        self, run_generator: Callable[[int], RawData]
    ) -> None:
        assert run_generator(11) == run_generator(11)

    def test_different_seed_changes_output(self, run_generator: Callable[[int], RawData]) -> None:
        assert run_generator(11)["customers"] != run_generator(12)["customers"]


class TestIntegrity:
    def test_all_records_validate_against_models(self, small_run: RawData) -> None:
        for name, rows in small_run.items():
            for row in rows:
                MODEL_BY_OBJECT[name].model_validate(row)

    def test_subscriptions_reference_existing_customers_and_prices(
        self, small_run: RawData
    ) -> None:
        customer_ids = {row["id"] for row in small_run["customers"]}
        price_ids = {row["id"] for row in small_run["prices"]}
        for subscription in small_run["subscriptions"]:
            assert subscription["customer"] in customer_ids
            assert items_of(subscription)["price"]["id"] in price_ids

    def test_events_are_chronological_per_subscription(self, small_run: RawData) -> None:
        last_seen: dict[str, int] = {}
        for event in small_run["events"]:  # written sorted by created
            subscription_id = event["data"]["object"]["id"]
            assert event["created"] >= last_seen.get(subscription_id, 0)
            last_seen[subscription_id] = event["created"]

    def test_every_subscription_has_a_created_event(self, small_run: RawData) -> None:
        created = {
            event["data"]["object"]["id"]
            for event in small_run["events"]
            if event["type"] == "customer.subscription.created"
        }
        assert created == {row["id"] for row in small_run["subscriptions"]}

    def test_final_event_snapshot_matches_subscription(self, small_run: RawData) -> None:
        latest: dict[str, dict[str, Any]] = {}
        for event in small_run["events"]:
            latest[event["data"]["object"]["id"]] = event["data"]["object"]
        for subscription in small_run["subscriptions"]:
            assert latest[subscription["id"]] == subscription

    def test_paid_invoices_have_a_succeeded_charge(self, small_run: RawData) -> None:
        paid_by_charge = {
            charge["metadata"]["invoice"]
            for charge in small_run["charges"]
            if charge["status"] == "succeeded"
        }
        for invoice in small_run["invoices"]:
            if invoice["status"] == "paid":
                assert invoice["id"] in paid_by_charge


class TestLifecyclePaths:
    def test_every_lifecycle_path_occurs(self, small_run: RawData) -> None:
        paths: Counter[str] = Counter()
        for subscription in small_run["subscriptions"]:
            reason = subscription["cancellation_details"]["reason"]
            if subscription["status"] == "canceled":
                if subscription["ended_at"] == subscription["trial_end"]:
                    paths["trial_lapse"] += 1
                elif reason == "payment_failed":
                    paths["involuntary_churn"] += 1
                else:
                    paths["voluntary_churn"] += 1
        for event in small_run["events"]:
            previous = event["data"]["previous_attributes"] or {}
            if "items" not in previous:
                continue
            before = items_of(previous)
            after = items_of(event["data"]["object"])
            if after["quantity"] != before["quantity"]:
                paths["seats_up" if after["quantity"] > before["quantity"] else "seats_down"] += 1
            before_amount = before["price"]["unit_amount"]
            after_amount = after["price"]["unit_amount"]
            if before["price"]["recurring"] != after["price"]["recurring"]:
                paths["switch_to_annual"] += 1
            elif after_amount > before_amount:
                paths["upgrade"] += 1
            elif after_amount < before_amount:
                paths["downgrade"] += 1
        subscriptions_per_customer = Counter(s["customer"] for s in small_run["subscriptions"])
        paths["reactivation"] = sum(1 for n in subscriptions_per_customer.values() if n > 1)

        expected = {
            "trial_lapse", "involuntary_churn", "voluntary_churn", "seats_up",
            "seats_down", "upgrade", "downgrade", "reactivation",
        }  # fmt: skip
        assert expected <= {path for path, count in paths.items() if count > 0}, paths

    def test_statuses_cover_active_and_canceled(self, small_run: RawData) -> None:
        statuses = Counter(row["status"] for row in small_run["subscriptions"])
        assert statuses["active"] > 0 and statuses["canceled"] > 0
