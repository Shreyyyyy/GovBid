/**
 * Connector for GeM (Government e-Marketplace) public bid data.
 *
 * Talks to the same public, anonymous, session+CSRF-protected JSON endpoint
 * (bidplus.gem.gov.in/all-bids-data) that GeM's own "All Bids" page uses to
 * render bid cards for any visitor - no login, no CAPTCHA, and robots.txt
 * permits crawling this path. We replicate exactly what a browser does:
 * load the public page once for a session cookie + CSRF token, then reuse
 * both for the same JSON calls the page itself makes. This is not an
 * authentication or anti-bot bypass - it is the site's own public contract.
 *
 * If GeM's firewall rejects the request outright (common for cloud/PaaS
 * datacenter IP ranges), that is reported as-is - this project does not
 * attempt to route around it.
 */

const GEM_ALL_BIDS_PAGE = "https://bidplus.gem.gov.in/all-bids";
const GEM_ALL_BIDS_DATA = "https://bidplus.gem.gov.in/all-bids-data";
const GEM_BASE_URL = "https://bidplus.gem.gov.in";
const MAX_PAGES = 5;

const CSRF_RE = /csrf_bd_gem_nk['"]?\s*:\s*['"]([a-f0-9]{16,64})['"]/;

export interface Bid {
  bidId: string;
  title: string;
  ministry: string | null;
  department: string | null;
  category: string | null;
  quantity: number | null;
  startDate: string | null;
  endDate: string | null;
  status: string;
  sourceUrl: string | null;
}

export interface GemSearchResult {
  bids: Bid[];
  totalFound: number;
  reachable: boolean;
  message: string;
}

interface GemFilters {
  keywords?: string[];
  category?: string[];
  ministry?: string[];
  status?: string | null;
}

function describeError(err: unknown): string {
  const cause = (err as any)?.cause;
  const code = cause?.code || (err as any)?.code;
  if (code === "ECONNREFUSED" || code === "ECONNRESET" || code === "ETIMEDOUT") {
    return (
      "Unavailable for automated access: could not open a connection to GeM " +
      `(${code}). GeM is reachable from ordinary residential/ISP connections, so this ` +
      "usually means GeM's firewall is blocking this server's network range (a common " +
      "anti-bot measure many Indian government sites apply to known cloud/PaaS datacenter " +
      "IPs). This is not a code bug and this project does not attempt to route around it. " +
      "Try running the app locally, or from infrastructure with a normal ISP egress IP."
    );
  }
  return `Unavailable for automated access: ${err instanceof Error ? err.message : String(err)}`;
}

async function fetchSessionToken(): Promise<{ token: string | null; cookie: string }> {
  const response = await fetch(GEM_ALL_BIDS_PAGE, {
    headers: { "User-Agent": "Mozilla/5.0 (compatible; GovBidIntelligence/0.1)" },
  });

  const setCookies = typeof response.headers.getSetCookie === "function" ? response.headers.getSetCookie() : [];
  const cookie = setCookies.map((c) => c.split(";")[0]).join("; ");

  if (response.status !== 200) return { token: null, cookie };

  const html = await response.text();
  const match = CSRF_RE.exec(html);
  return { token: match ? match[1] : null, cookie };
}

function first<T>(value: T | T[] | undefined | null): T | null {
  if (Array.isArray(value)) return value.length ? value[0] : null;
  return (value as T) ?? null;
}

function parseGemDate(value: unknown): string | null {
  const v = first<string>(value as string | string[]);
  if (!v || v.startsWith("-")) return null;
  return v.slice(0, 19).replace("T", " ");
}

const DOC_LABEL_BY_BID_TYPE: Record<number, string> = { 5: "showdirectradocumentPdf", 2: "showradocumentPdf" };

function normalizeDoc(doc: any): Bid {
  const bidId = first<number>(doc.b_id);
  const bidType = first<number>(doc.b_bid_type);
  const docLabel = (bidType && DOC_LABEL_BY_BID_TYPE[bidType]) || "showbidDocument";
  const ministry = first<string>(doc.ba_official_details_minName);
  let department = first<string>(doc.ba_official_details_deptName);
  if (department === "NA" || department === "") department = null;

  return {
    bidId: first<string>(doc.b_bid_number) || `#${bidId}`,
    title: first<string>(doc.b_category_name) || "Untitled GeM bid",
    ministry,
    department,
    category: first<string>(doc.b_category_name),
    quantity: first<number>(doc.b_total_quantity),
    startDate: parseGemDate(doc.final_start_date_sort),
    endDate: parseGemDate(doc.final_end_date_sort),
    status: "ACTIVE",
    sourceUrl: bidId ? `${GEM_BASE_URL}/${docLabel}/${bidId}` : null,
  };
}

export async function searchGem(filters: GemFilters): Promise<GemSearchResult> {
  let token: string | null;
  let cookie: string;

  try {
    ({ token, cookie } = await fetchSessionToken());
  } catch (err) {
    return { bids: [], totalFound: 0, reachable: false, message: describeError(err) };
  }

  if (!token) {
    return {
      bids: [],
      totalFound: 0,
      reachable: false,
      message: "Unavailable for automated access: could not obtain GeM's public page session token (the page format may have changed).",
    };
  }

  const keywordParts = [...(filters.keywords || []), ...(filters.category || [])];
  const searchText = keywordParts.join(" ").trim();

  const param: Record<string, unknown> = { searchType: "fullText" };
  if (searchText) param.searchBid = searchText;
  const bidFilter: Record<string, unknown> = { bidStatusType: "ongoing_bids", byType: "all" };
  if (filters.status === "CLOSED") bidFilter.bidStatusType = "bidrastatus";

  const allBids: Bid[] = [];
  let totalFound = 0;

  try {
    for (let page = 1; page <= MAX_PAGES; page++) {
      const payload: Record<string, unknown> = { param, filter: bidFilter };
      if (page > 1) payload.page = page;

      const body = new URLSearchParams({
        payload: JSON.stringify(payload),
        csrf_bd_gem_nk: token,
      });

      const response = await fetch(GEM_ALL_BIDS_DATA, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-Requested-With": "XMLHttpRequest",
          Referer: GEM_ALL_BIDS_PAGE,
          Origin: GEM_BASE_URL,
          Cookie: cookie,
          "User-Agent": "Mozilla/5.0 (compatible; GovBidIntelligence/0.1)",
        },
        body,
      });

      if (!response.ok) break;
      const data = await response.json();
      if (data?.code !== 200) break;

      const block = data?.response?.response;
      totalFound = block?.numFound ?? totalFound;
      const docs: any[] = block?.docs || [];
      if (!docs.length) break;

      allBids.push(...docs.map(normalizeDoc));
      if (allBids.length >= totalFound) break;
    }
  } catch (err) {
    return { bids: allBids, totalFound, reachable: false, message: describeError(err) };
  }

  return {
    bids: allBids,
    totalFound,
    reachable: true,
    message: `Fetched ${allBids.length} of ${totalFound} matching bids from GeM (page size limited to ${MAX_PAGES} pages).`,
  };
}
