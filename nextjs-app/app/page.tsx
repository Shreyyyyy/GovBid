"use client";

import { useState } from "react";
import type { Bid } from "@/lib/gem";

const GEM_ALL_BIDS_URL = "https://bidplus.gem.gov.in/all-bids";

interface Filters {
  ministry: string;
  category: string;
  status: string;
  minQuantity: string;
  maxQuantity: string;
}

const emptyFilters: Filters = { ministry: "", category: "", status: "", minQuantity: "", maxQuantity: "" };

export default function Home() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [loading, setLoading] = useState(false);
  const [bids, setBids] = useState<Bid[] | null>(null);
  const [message, setMessage] = useState<{ text: string; reachable: boolean } | null>(null);

  async function runSearch() {
    setLoading(true);
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, filters }),
      });
      const data = await res.json();
      setBids(data.bids);
      setMessage({ text: data.message, reachable: data.reachable });
    } catch (err) {
      setBids([]);
      setMessage({ text: `Request failed: ${err instanceof Error ? err.message : String(err)}`, reachable: false });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1>📋 GovBid Intelligence</h1>
      <p className="subtitle">
        Live natural-language search over{" "}
        <a href={GEM_ALL_BIDS_URL} target="_blank" rel="noreferrer">
          GeM (Government e-Marketplace)
        </a>{" "}
        public bid data.
      </p>

      <div className="search-row">
        <input
          type="text"
          placeholder='Search GeM bids, e.g. "desktop computer bids from Ministry of Railways"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
        />
        <button className="btn-primary" onClick={runSearch} disabled={loading}>
          {loading ? "Searching..." : "🔍 Search GeM"}
        </button>
      </div>

      <details className="filters">
        <summary>➕ Add filters (optional)</summary>
        <div className="filter-grid">
          <input
            type="text"
            placeholder="Ministry, e.g. Ministry of Railways"
            value={filters.ministry}
            onChange={(e) => setFilters({ ...filters, ministry: e.target.value })}
          />
          <input
            type="text"
            placeholder="Category, e.g. Desktop Computer"
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
          />
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">Any status</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="CLOSED">CLOSED</option>
          </select>
          <input
            type="text"
            placeholder="Minimum Quantity"
            value={filters.minQuantity}
            onChange={(e) => setFilters({ ...filters, minQuantity: e.target.value })}
          />
        </div>
      </details>

      <hr className="divider" />

      {bids === null && !loading && (
        <p className="status-caption">
          Try: &quot;laptop tenders&quot; · &quot;printers closing this week&quot; · &quot;networking equipment&quot; — every search
          queries GeM live.
        </p>
      )}

      {message && (
        <>
          <div className="results-header">
            <h3>{bids?.length ?? 0} bid(s) found</h3>
          </div>
          <p className="status-caption">
            {message.reachable ? "✅" : "⚠️"} GeM: {message.text}
          </p>
        </>
      )}

      {bids && bids.length === 0 && (
        <div className="empty-state">No bids match. Try a different search term, or clear the optional filters above.</div>
      )}

      {bids?.map((bid) => (
        <BidCard key={bid.sourceUrl || bid.bidId} bid={bid} />
      ))}
    </div>
  );
}

function BidCard({ bid }: { bid: Bid }) {
  const statusClass =
    bid.status === "ACTIVE" ? "badge-active" : bid.status === "CLOSED" ? "badge-closed" : "badge-unknown";

  return (
    <div className="bid-card">
      <p className="bid-no">
        BID NO:{" "}
        {bid.sourceUrl ? (
          <a href={bid.sourceUrl} target="_blank" rel="noreferrer">
            {bid.bidId} 🔗
          </a>
        ) : (
          bid.bidId
        )}
      </p>
      <p className="bid-items">
        <strong>Items:</strong> {bid.title}
      </p>

      <div className="metric-row">
        <div className="metric">
          <div className="metric-label">Quantity</div>
          <div className="metric-value">{bid.quantity ?? "N/A"}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Start Date</div>
          <div className="metric-value">{bid.startDate ?? "N/A"}</div>
        </div>
        <div className="metric">
          <div className="metric-label">End Date</div>
          <div className="metric-value">{bid.endDate ?? "N/A"}</div>
        </div>
      </div>

      <div className="dept-block">
        <strong>Department Name And Address:</strong>
        <br />
        {bid.ministry || "Not specified"}
        {bid.department ? <><br />{bid.department}</> : null}
      </div>

      <div className="card-footer">
        <span className={`badge ${statusClass}`}>{bid.status}</span>
        {bid.sourceUrl && (
          <a className="link-btn" href={bid.sourceUrl} target="_blank" rel="noreferrer">
            🔗 View on GeM ↗
          </a>
        )}
      </div>
    </div>
  );
}
