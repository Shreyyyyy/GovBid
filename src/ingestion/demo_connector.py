"""Demo data connector for local development/testing only.

Every record is clearly marked source="DEMO" and is_demo=True so the UI can
render an unmistakable warning. Demo records must never be presented as
real government data.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from src.ingestion.base_connector import BaseConnector, SearchResult, SourceStatus

_DEMO_BIDS = [
    {
        "bid_id": "DEMO-2026-IT-001",
        "title": "Supply of Desktop Computers (Core i5, 8GB RAM)",
        "description": "Procurement of branded desktop computers for departmental offices.",
        "organization": "Department of Expenditure",
        "ministry": "Ministry of Finance",
        "department": "Department of Expenditure",
        "buyer_name": "Deputy Secretary (IT)",
        "category": "Computers & IT",
        "subcategory": "Desktop Computers",
        "quantity": 250,
        "estimated_value": 1_25_00_000.0,
        "currency": "INR",
        "bid_start_date": dt.date.today() - dt.timedelta(days=5),
        "bid_end_date": dt.date.today() + dt.timedelta(days=10),
        "status": "ACTIVE",
        "delivery_location": "New Delhi",
        "state": "Delhi",
        "city": "New Delhi",
        "eligibility": "OEM authorization required; minimum annual turnover Rs. 5 crore.",
        "oem_required": True,
        "mse_preference": True,
        "startup_preference": False,
        "turnover_requirement": "Rs. 5 crore (average of last 3 years)",
        "documents": [],
    },
    {
        "bid_id": "DEMO-2026-IT-002",
        "title": "Procurement of Laptops for Field Staff",
        "description": "Supply and installation of laptops with 3-year onsite warranty.",
        "organization": "Central Board of Direct Taxes",
        "ministry": "Ministry of Finance",
        "department": "Central Board of Direct Taxes",
        "buyer_name": "Under Secretary",
        "category": "Computers & IT",
        "subcategory": "Laptops",
        "quantity": 100,
        "estimated_value": 90_00_000.0,
        "currency": "INR",
        "bid_start_date": dt.date.today() - dt.timedelta(days=2),
        "bid_end_date": dt.date.today() + dt.timedelta(days=20),
        "status": "ACTIVE",
        "delivery_location": "Mumbai",
        "state": "Maharashtra",
        "city": "Mumbai",
        "eligibility": "MSE preference applicable.",
        "oem_required": False,
        "mse_preference": True,
        "startup_preference": True,
        "turnover_requirement": "Rs. 2 crore (average of last 3 years)",
        "documents": [],
    },
    {
        "bid_id": "DEMO-2026-IT-003",
        "title": "Annual Maintenance Contract for Networking Equipment",
        "description": "AMC for routers, switches and firewall appliances.",
        "organization": "Ministry of Electronics and IT",
        "ministry": "Ministry of Electronics and Information Technology",
        "department": "NIC",
        "buyer_name": "Director (Systems)",
        "category": "Computers & IT",
        "subcategory": "Networking",
        "quantity": 1,
        "estimated_value": 45_00_000.0,
        "currency": "INR",
        "bid_start_date": dt.date.today() - dt.timedelta(days=30),
        "bid_end_date": dt.date.today() - dt.timedelta(days=1),
        "status": "CLOSED",
        "delivery_location": "New Delhi",
        "state": "Delhi",
        "city": "New Delhi",
        "eligibility": "Past experience of at least 2 similar AMC contracts.",
        "oem_required": True,
        "mse_preference": False,
        "startup_preference": False,
        "turnover_requirement": "Rs. 3 crore (average of last 3 years)",
        "documents": [],
    },
]


class DemoConnector(BaseConnector):
    name = "DEMO"

    def health_check(self) -> SourceStatus:
        return SourceStatus(source=self.name, reachable=True, message="Local demo data (not live government data).")

    def search(self, filters: dict[str, Any]) -> SearchResult:
        bids = [self.normalize({**b, "source_url": None}) for b in _DEMO_BIDS]
        return SearchResult(
            bids=bids,
            status=SourceStatus(source=self.name, reachable=True, message=f"Loaded {len(bids)} demo records."),
        )

    def fetch_bid(self, bid_id: str) -> Optional[dict[str, Any]]:
        for b in _DEMO_BIDS:
            if b["bid_id"] == bid_id:
                return self.normalize(dict(b))
        return None

    def fetch_documents(self, bid: dict[str, Any]) -> list[dict[str, Any]]:
        return []
