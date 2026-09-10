import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import RawData

from revenue_monitor.raw_io import RAW_OBJECTS, read_jsonl
from revenue_monitor.stripe_source import LiveKeyError, extract, require_test_key


class FakeStripeObject:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload


class FakePage:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._payloads = payloads

    def auto_paging_iter(self) -> Iterator[FakeStripeObject]:
        return iter(FakeStripeObject(payload) for payload in self._payloads)


class FakeResource:
    """Serves generated records, honouring the ``created[gt]`` cursor like Stripe."""

    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._payloads = payloads
        self.calls: list[dict[str, Any]] = []

    def list(self, params: dict[str, Any]) -> FakePage:
        self.calls.append(params)
        cursor = params.get("created", {}).get("gt", -1)
        return FakePage([p for p in self._payloads if p["created"] > cursor])


class FakeApi:
    def __init__(self, data: RawData) -> None:
        for name in RAW_OBJECTS:
            setattr(self, name, FakeResource(data[name][:25]))


class TestExtract:
    def test_extract_writes_records_and_advances_cursor(
        self, small_run: RawData, tmp_path: Path
    ) -> None:
        api = FakeApi(small_run)
        counts = extract(api, tmp_path)

        assert counts["customers"] == 25
        written = list((tmp_path / "customers").glob("stripe_*.jsonl"))
        assert len(written) == 1
        assert len(list(read_jsonl(written[0]))) == 25
        state = json.loads((tmp_path / "_stripe_state.json").read_text())
        assert state["customers"] == small_run["customers"][24]["created"]

    def test_second_run_only_asks_for_newer_objects(
        self, small_run: RawData, tmp_path: Path
    ) -> None:
        api = FakeApi(small_run)
        extract(api, tmp_path)
        counts = extract(api, tmp_path)

        assert all(count == 0 for count in counts.values())
        assert "created" in api.customers.calls[-1]  # type: ignore[attr-defined]

    def test_extract_requests_all_subscription_statuses(
        self, small_run: RawData, tmp_path: Path
    ) -> None:
        api = FakeApi(small_run)
        extract(api, tmp_path)
        assert api.subscriptions.calls[0]["status"] == "all"  # type: ignore[attr-defined]


class TestRequireTestKey:
    def test_live_key_is_rejected(self) -> None:
        with pytest.raises(LiveKeyError):
            require_test_key("sk_live_abc")

    def test_test_key_is_accepted(self) -> None:
        require_test_key("sk_test_abc")
