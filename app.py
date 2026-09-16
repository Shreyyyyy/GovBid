"""GovBid Intelligence - live natural-language search over GeM public bid data.

Run with: streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import io

import pandas as pd
import streamlit as st
from sqlalchemy import or_

from src.ai.bid_analyzer import BidAnalyzer
from src.ai.query_parser import ParsedQuery, QueryParser
from src.config import settings
from src.database import get_session, init_db
from src.extraction.pdf_extractor import PDFExtractionError, extract_pdf
from src.models import Bid, BidDocument
from src.services import bid_service
from src.services.ingestion_service import fetch_documents_for_bid, run_source
from src.utils.currency import format_inr, parse_inr

st.set_page_config(page_title="GovBid Intelligence", page_icon="📋", layout="centered")

init_db()

GEM_SOURCE_NAME = "gem"
GEM_ALL_BIDS_URL = "https://bidplus.gem.gov.in/all-bids"

DEFAULT_STATE = {
    "view": "search",
    "search_query": "",
    "parsed_query": None,
    "selected_bid_id": None,
    "chat_history": {},
    "last_gem_log": None,
    "last_matched_bid_ids": None,
    "active_filters": None,
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def goto(view: str, **kwargs) -> None:
    st.session_state["view"] = view
    for k, v in kwargs.items():
        st.session_state[k] = v


_STATUS_BADGE_COLOR = {"ACTIVE": "green", "CLOSED": "red", "UPCOMING": "blue"}


def status_badge_md(status: str | None) -> str:
    status = (status or "UNKNOWN").upper()
    color = _STATUS_BADGE_COLOR.get(status, "gray")
    return f":{color}-badge[{status}]"


def demo_badge_md(is_demo: bool) -> str:
    return " :orange-badge[⚠ DEMO DATA]" if is_demo else ""


_SOURCE_DISPLAY_NAMES = {"gem": "GeM", "cppp": "CPPP", "ministry": "Ministry", "demo": "Demo"}


def source_display_name(source: str | None) -> str:
    return _SOURCE_DISPLAY_NAMES.get((source or "").lower(), source or "Unknown")


def _yesno(value) -> str:
    if value is None:
        return "Not specified"
    return "Yes" if value else "No"


def _gem_raw_datetime(bid: Bid, key: str) -> str:
    """Format a GeM raw timestamp the way GeM's own bid cards do:
    'DD-MM-YYYY H:MM AM/PM'. Falls back to the normalized date-only field."""
    raw = bid.raw_data or {}
    value = raw.get(key)
    if isinstance(value, list):
        value = value[0] if value else None

    if isinstance(value, str) and not value.startswith("-"):
        try:
            parsed = dt.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
            hour12 = parsed.hour % 12 or 12
            ampm = "AM" if parsed.hour < 12 else "PM"
            return f"{parsed.strftime('%d-%m-%Y')} {hour12}:{parsed.minute:02d} {ampm}"
        except ValueError:
            pass

    fallback_field = bid.bid_start_date if "start" in key else bid.bid_end_date
    return fallback_field.strftime("%d-%m-%Y") if fallback_field else "N/A"


def render_gem_bid_card(bid: Bid, show_details_button: bool = False) -> None:
    """A big, at-a-glance summary matching how GeM itself presents a bid."""
    with st.container(border=True):
        bid_no = bid.bid_id or f"#{bid.id}"
        if bid.source_url:
            st.markdown(f"##### BID NO: [{bid_no}]({bid.source_url}) 🔗")
        else:
            st.markdown(f"##### BID NO: {bid_no}")

        is_demo = bid.is_demo or (bid.source or "").upper() == "DEMO"
        st.markdown(f"**Items:** {bid.title or 'N/A'}{demo_badge_md(is_demo)}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Quantity", bid.quantity if bid.quantity is not None else "N/A")
        c2.metric("Start Date", _gem_raw_datetime(bid, "final_start_date_sort"))
        c3.metric("End Date", _gem_raw_datetime(bid, "final_end_date_sort"))

        dept_lines = [line for line in (bid.ministry, bid.department) if line]
        st.markdown("**Department Name And Address:**")
        st.markdown("  \n".join(dept_lines) if dept_lines else "_Not specified_")

        footer1, footer2, footer3 = st.columns([1, 1.4, 1.4])
        footer1.markdown(status_badge_md(bid.status))
        if bid.source_url:
            footer2.link_button("🔗 View on GeM ↗", bid.source_url)
        if show_details_button:
            if footer3.button("📄 Details & AI Analysis", key=f"details_{bid.id}"):
                goto("bid_detail", selected_bid_id=bid.id)
                st.rerun()


# --------------------------------------------------------------------------
# SEARCH
# --------------------------------------------------------------------------
def run_search(query: str, manual_filters: dict) -> None:
    """Parse the query, overlay any manually-set filters, and run a live
    GeM search for the merged filter set."""
    with get_session() as session:
        parser = QueryParser()
        try:
            parsed = parser.parse(query) if query.strip() else ParsedQuery()
        except Exception:
            parsed = ParsedQuery()

        merged = parsed.model_dump()
        for field, value in manual_filters.items():
            if value:
                merged[field] = value
        parsed = ParsedQuery.model_validate(merged)
        st.session_state["parsed_query"] = parsed.model_dump()

        with st.spinner("Searching GeM live..."):
            log = run_source(session, GEM_SOURCE_NAME, parsed.model_dump())
        st.session_state["last_gem_log"] = {"status": log.status, "message": log.message}
        st.session_state["last_matched_bid_ids"] = list(getattr(log, "matched_bid_ids", []) or [])

    st.session_state["search_query"] = query


def render_filters() -> dict:
    """Optional filter fields. Empty by default - only applied if the user
    fills them in."""
    with st.expander("➕ Add filters (optional)"):
        c1, c2 = st.columns(2)
        ministry = c1.text_input("Ministry", placeholder="e.g. Ministry of Railways")
        category = c2.text_input("Category", placeholder="e.g. Desktop Computer")

        c3, c4 = st.columns(2)
        status = c3.selectbox("Status", ["", "ACTIVE", "CLOSED", "UPCOMING"])
        min_qty = c4.text_input("Minimum Quantity")

        c5, c6 = st.columns(2)
        min_value = c5.text_input("Minimum Value (₹)", placeholder="e.g. 10 lakh")
        max_value = c6.text_input("Maximum Value (₹)", placeholder="e.g. 1 crore")

    return {
        "ministry": [ministry] if ministry else [],
        "category": [category] if category else [],
        "status": status or None,
        "min_quantity": float(min_qty) if min_qty else None,
        "min_value": parse_inr(min_value) if min_value else None,
        "max_value": parse_inr(max_value) if max_value else None,
    }


def _apply_manual_filters(query, filters: dict):
    """Apply only the fields the user explicitly set in the filter boxes.
    Nothing the query parser silently inferred (status, dates, semantic
    hints, etc.) ever reaches this - it's a plain, predictable AND of
    whatever is non-empty here."""
    if filters.get("ministry"):
        query = query.filter(or_(*[Bid.ministry.ilike(f"%{m}%") for m in filters["ministry"]]))
    if filters.get("category"):
        query = query.filter(or_(*[Bid.category.ilike(f"%{c}%") for c in filters["category"]]))
    if filters.get("status"):
        query = query.filter(Bid.status == filters["status"])
    if filters.get("min_quantity") is not None:
        query = query.filter(Bid.quantity >= filters["min_quantity"])
    if filters.get("min_value") is not None:
        query = query.filter(Bid.estimated_value >= filters["min_value"])
    if filters.get("max_value") is not None:
        query = query.filter(Bid.estimated_value <= filters["max_value"])
    return query


def render_search_page() -> None:
    st.markdown("# 📋 GovBid Intelligence")
    st.markdown(
        f"##### Live natural-language search over [GeM (Government e-Marketplace)]({GEM_ALL_BIDS_URL}) public bid data."
    )
    if not settings.has_groq_key:
        st.warning("Groq API key not configured — search will fall back to plain keyword matching, and AI analysis will be unavailable.", icon="⚠️")

    query = st.text_input(
        "Search",
        placeholder='Search GeM bids, e.g. "desktop computer bids from Ministry of Railways"',
        label_visibility="collapsed",
        value=st.session_state.get("search_query", ""),
        key="search_query_input",
    )
    manual_filters = render_filters()
    search_clicked = st.button("🔍 Search GeM", type="primary")

    if search_clicked:
        st.session_state["active_filters"] = manual_filters
        run_search(query, manual_filters)
        st.rerun()

    st.divider()

    parsed_dict = st.session_state.get("parsed_query")
    if parsed_dict is None:
        st.caption(f'Try: "laptop tenders" · "printers closing this week" · "networking equipment above 10 lakh" — every search queries [GeM]({GEM_ALL_BIDS_URL}) live.')
        return

    matched_ids = st.session_state.get("last_matched_bid_ids")
    active_filters = st.session_state.get("active_filters") or {}

    with get_session() as session:
        base_query = session.query(Bid)
        if matched_ids:
            # Show exactly what GeM's own search returned for this query.
            # Only the filter boxes you explicitly fill in narrow this
            # further - nothing the query parser silently inferred (status,
            # dates, etc.) is applied here, so a search never comes back
            # empty for reasons that aren't visible on screen.
            base_query = base_query.filter(Bid.id.in_(matched_ids))
        query_obj = _apply_manual_filters(base_query, active_filters)
        bids = query_obj.order_by(Bid.bid_end_date.asc().nullslast()).all()

        header_col, refresh_col = st.columns([3, 1])
        header_col.markdown(f"### {len(bids)} bid(s) found")
        if refresh_col.button("🔄 Refresh"):
            st.session_state["active_filters"] = manual_filters
            run_search(st.session_state.get("search_query", ""), manual_filters)
            st.rerun()

        last_log = st.session_state.get("last_gem_log")
        if last_log:
            icon = "✅" if last_log["status"] == "OK" else "⚠️"
            st.caption(f"{icon} GeM: {last_log['message']}")

        active_bits = []
        if active_filters.get("ministry"):
            active_bits.append(f"Ministry: {active_filters['ministry'][0]}")
        if active_filters.get("category"):
            active_bits.append(f"Category: {active_filters['category'][0]}")
        if active_filters.get("status"):
            active_bits.append(f"Status: {active_filters['status']}")
        if active_filters.get("min_quantity") is not None:
            active_bits.append(f"Min Qty: {active_filters['min_quantity']:g}")
        if active_filters.get("min_value") is not None:
            active_bits.append(f"Min Value: {format_inr(active_filters['min_value'])}")
        if active_filters.get("max_value") is not None:
            active_bits.append(f"Max Value: {format_inr(active_filters['max_value'])}")
        if active_bits:
            st.caption("🔎 Filtered by " + " · ".join(active_bits))

        if not bids:
            st.info("No bids match. Try a different search term, or clear the optional filters above.")
            return

        with st.expander("⬇️ Export these results"):
            rows = [
                {
                    "Bid No": b.bid_id or f"#{b.id}",
                    "Items": b.title,
                    "Ministry": b.ministry,
                    "Department": b.department,
                    "Quantity": b.quantity,
                    "Value": format_inr(b.estimated_value),
                    "Start Date": _gem_raw_datetime(b, "final_start_date_sort"),
                    "End Date": _gem_raw_datetime(b, "final_end_date_sort"),
                    "Status": b.status,
                    "Link": b.source_url,
                }
                for b in bids
            ]
            df = pd.DataFrame(rows)
            e1, e2, e3 = st.columns(3)
            e1.download_button("CSV", df.to_csv(index=False).encode("utf-8"), file_name="gem_bids.csv", mime="text/csv")
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Bids")
            e2.download_button(
                "Excel", excel_buffer.getvalue(), file_name="gem_bids.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            e3.download_button("JSON", df.to_json(orient="records", indent=2), file_name="gem_bids.json", mime="application/json")

        for bid in bids:
            render_gem_bid_card(bid, show_details_button=True)


# --------------------------------------------------------------------------
# BID DETAIL
# --------------------------------------------------------------------------
def render_bid_detail() -> None:
    bid_pk = st.session_state.get("selected_bid_id")
    if not bid_pk:
        st.warning("No bid selected.")
        return

    with get_session() as session:
        bid = bid_service.get_bid(session, bid_pk)
        if not bid:
            st.error("Bid not found.")
            return

        if st.button("← Back to search"):
            goto("search")
            st.rerun()

        render_gem_bid_card(bid)

        tabs = st.tabs(["Overview", "Technical", "Eligibility", "Commercial", "Documents", "AI Analysis", "Ask This Bid", "Sources"])

        with tabs[0]:
            st.markdown(f"**Ministry:** {bid.ministry or 'N/A'}")
            st.markdown(f"**Department:** {bid.department or 'N/A'}")
            st.markdown(f"**Buyer:** {bid.buyer_name or 'N/A'}")
            st.markdown(f"**Category:** {bid.category or 'N/A'} / {bid.subcategory or 'N/A'}")
            st.markdown(f"**Description:** {bid.description or 'N/A'}")

        with tabs[1]:
            st.markdown(bid.technical_requirements or "_No technical requirements captured from metadata yet. Try AI Analysis after fetching documents._")

        with tabs[2]:
            st.markdown(f"**Eligibility:** {bid.eligibility or 'N/A'}")
            st.markdown(f"**OEM Required:** {_yesno(bid.oem_required)}")
            st.markdown(f"**Turnover Requirement:** {bid.turnover_requirement or 'N/A'}")
            st.markdown(f"**Past Experience:** {bid.past_experience_requirement or 'N/A'}")
            st.markdown(f"**MSE Preference:** {_yesno(bid.mse_preference)}")
            st.markdown(f"**Startup Preference:** {_yesno(bid.startup_preference)}")

        with tabs[3]:
            st.markdown(f"**Estimated Value:** {format_inr(bid.estimated_value)}")
            st.markdown(f"**Financial Requirements:** {bid.financial_requirements or 'N/A'}")

        with tabs[4]:
            render_documents_tab(session, bid)

        with tabs[5]:
            render_ai_analysis_tab(bid)

        with tabs[6]:
            render_ask_bid_tab(bid)

        with tabs[7]:
            render_sources_tab(bid)


def render_documents_tab(session, bid: Bid) -> None:
    if bid.documents:
        for doc in bid.documents:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{doc.name}**")
                c1.caption(f"Type: {doc.doc_type or 'PDF'} · Pages: {doc.page_count or 'N/A'}")
                if doc.source_url:
                    c2.link_button("Open Source", doc.source_url)
                if doc.local_path:
                    try:
                        with open(doc.local_path, "rb") as fh:
                            c3.download_button("Download", fh.read(), file_name=doc.name, key=f"dl_{doc.id}")
                    except OSError:
                        c3.caption("File unavailable locally.")
                if doc.extraction_empty:
                    st.warning("Text extraction was empty for this document (scanned/image-only PDF and OCR unavailable).")
    else:
        st.info("No documents indexed yet for this bid.")

    if bid.source_url and (bid.source or "").upper() != "DEMO":
        if st.button("📥 Fetch documents from source"):
            with st.spinner(f"Fetching documents from {source_display_name(bid.source)}..."):
                fetched = fetch_documents_for_bid(session, bid)
            if fetched:
                st.success(f"Fetched and extracted {len(fetched)} document(s).")
                st.rerun()
            else:
                st.warning(
                    "No document could be retrieved automatically from this source right now "
                    "(it may not be available for automated download). Use the manual upload "
                    "below, or open the source link directly."
                )

    st.markdown("##### Manually upload a tender document")
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], key=f"upload_{bid.id}")
    if uploaded is not None and st.button("Process document"):
        from src.config import DOCUMENTS_DIR

        dest = DOCUMENTS_DIR / f"bid{bid.id}_{uploaded.name}"
        dest.write_bytes(uploaded.getvalue())
        try:
            result = extract_pdf(dest)
        except PDFExtractionError as exc:
            st.error(f"Extraction failed: {exc}")
            return

        doc = BidDocument(
            bid=bid,
            name=uploaded.name,
            doc_type="PDF",
            local_path=str(dest),
            file_hash=result.file_hash,
            page_count=result.page_count,
            extraction_empty=result.extraction_empty,
            used_ocr=result.used_ocr,
            extracted_pages=[{"page": p.page, "text": p.text} for p in result.pages],
        )
        session.add(doc)
        st.success(f"Processed {uploaded.name}: {result.page_count} pages extracted.")
        st.rerun()


def _doc_hash_signature(bid: Bid) -> list[str]:
    return sorted([d.file_hash for d in bid.documents if d.file_hash])


def render_ai_analysis_tab(bid: Bid) -> None:
    if not settings.has_groq_key:
        st.warning("Groq API key not configured. AI analysis is unavailable.")
        return

    current_sig = _doc_hash_signature(bid)
    cache = bid.analysis_cache or {}
    cached_result = cache.get("result")
    cached_sig = cache.get("doc_hashes")

    if st.button("🤖 Analyze with Groq", type="primary"):
        documents = [
            {"name": d.name, "pages": d.extracted_pages or []}
            for d in bid.documents
            if d.extracted_pages
        ]
        bid_meta = {
            "title": bid.title,
            "quantity": bid.quantity,
            "category": bid.category,
            "estimated_value": bid.estimated_value,
            "delivery_location": bid.delivery_location,
        }
        with st.spinner("Analyzing with Groq..."):
            analyzer = BidAnalyzer()
            result = analyzer.analyze(bid_meta, documents)
        bid.analysis_cache = {"result": result, "doc_hashes": current_sig, "analyzed_at": dt.datetime.utcnow().isoformat()}
        cached_result = result
        st.rerun()

    if cached_result and cached_sig == current_sig:
        _render_analysis_result(cached_result)
    elif cached_result:
        st.info("Documents changed since the last analysis. Click 'Analyze with Groq' to refresh.")
        _render_analysis_result(cached_result)
    else:
        st.info("No analysis yet. Click 'Analyze with Groq' to generate one from indexed documents.")


def _render_analysis_result(result: dict) -> None:
    if "error" in result:
        st.error(result["error"])
        return

    st.markdown("#### Summary")
    st.write(result.get("summary") or "N/A")

    proc = result.get("procurement") or {}
    st.markdown("#### Procurement")
    st.write(f"What: {proc.get('what', 'N/A')} · Quantity: {proc.get('quantity', 'N/A')} · Category: {proc.get('category', 'N/A')}")

    st.markdown("#### Technical Requirements")
    _render_cited_list(result.get("technical_requirements") or [])

    elig = result.get("eligibility") or {}
    st.markdown("#### Eligibility")
    st.write(f"OEM: {elig.get('oem', 'N/A')} · Turnover: {elig.get('turnover', 'N/A')} · Experience: {elig.get('experience', 'N/A')} · Certifications: {elig.get('certifications', 'N/A')}")

    comm = result.get("commercial") or {}
    st.markdown("#### Commercial")
    st.write(f"Bid Value: {comm.get('bid_value', 'N/A')} · EMD: {comm.get('emd', 'N/A')} · Security: {comm.get('security', 'N/A')} · Payment Terms: {comm.get('payment_terms', 'N/A')}")

    delivery = result.get("delivery") or {}
    st.markdown("#### Delivery")
    st.write(f"Location: {delivery.get('location', 'N/A')} · Period: {delivery.get('period', 'N/A')}")

    st.markdown("#### Important Dates")
    _render_cited_list(result.get("important_dates") or [], value_key="label")

    st.markdown("#### Documents Required")
    _render_cited_list(result.get("documents_required") or [])

    st.markdown("#### Important Notes")
    st.info(result.get("important_notes") or "None.")


def _render_cited_list(items: list, value_key: str = "value") -> None:
    if not items:
        st.write("_None specified._")
        return
    for item in items:
        if isinstance(item, dict):
            value = item.get(value_key) or item.get("value") or ""
            doc = item.get("document")
            page = item.get("page")
            source_note = f" — *{doc}, Page {page}*" if doc else ""
            st.markdown(f"- {value}{source_note}")
        else:
            st.markdown(f"- {item}")


def render_ask_bid_tab(bid: Bid) -> None:
    if not settings.has_groq_key:
        st.warning("Groq API key not configured. Ask-This-Bid is unavailable.")
        return

    history_key = f"chat_{bid.id}"
    history = st.session_state["chat_history"].setdefault(history_key, [])

    for role, text in history:
        with st.chat_message(role):
            st.markdown(text)

    question = st.chat_input("Ask a question about this bid...")
    if question:
        history.append(("user", question))
        documents = [
            {"name": d.name, "pages": d.extracted_pages or []}
            for d in bid.documents
            if d.extracted_pages
        ]
        analyzer = BidAnalyzer()
        with st.spinner("Thinking..."):
            answer = analyzer.ask(question, documents)
        history.append(("assistant", answer))
        st.rerun()


def render_sources_tab(bid: Bid) -> None:
    st.markdown(f"**Primary source:** {source_display_name(bid.source)}")
    if bid.source_url:
        st.link_button("🔗 View on GeM ↗", bid.source_url)
    if bid.additional_source_urls:
        st.markdown("**Additional sources:**")
        for url in bid.additional_source_urls:
            st.markdown(f"- [{url}]({url})")
    if not bid.source_url and not bid.additional_source_urls:
        st.info("No source URL recorded for this bid.")


# --------------------------------------------------------------------------
# ROUTER
# --------------------------------------------------------------------------
VIEW_RENDERERS = {
    "search": render_search_page,
    "bid_detail": render_bid_detail,
}

VIEW_RENDERERS.get(st.session_state["view"], render_search_page)()
