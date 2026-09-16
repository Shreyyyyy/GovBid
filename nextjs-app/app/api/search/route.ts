import { NextResponse } from "next/server";
import { parseQuery } from "@/lib/groq";
import { searchGem, type Bid } from "@/lib/gem";

interface ManualFilters {
  ministry?: string;
  category?: string;
  status?: string;
  minQuantity?: string;
  maxQuantity?: string;
}

export async function POST(req: Request) {
  const { query, filters } = (await req.json()) as { query: string; filters: ManualFilters };

  const parsed = await parseQuery(query || "");

  const ministry = filters?.ministry?.trim();
  const category = filters?.category?.trim();
  const status = filters?.status?.trim();
  const minQuantity = filters?.minQuantity ? parseFloat(filters.minQuantity) : null;
  const maxQuantity = filters?.maxQuantity ? parseFloat(filters.maxQuantity) : null;

  const gemFilters = {
    keywords: parsed.keywords,
    category: category ? [category] : parsed.category,
    ministry: ministry ? [ministry] : parsed.ministry,
    status: status || parsed.status,
  };

  const result = await searchGem(gemFilters);

  // Only the explicit filter boxes narrow the result set further - nothing
  // the query parser silently inferred does, so a search never comes back
  // empty for a reason invisible on screen.
  let bids: Bid[] = result.bids;
  if (ministry) bids = bids.filter((b) => b.ministry?.toLowerCase().includes(ministry.toLowerCase()));
  if (status) bids = bids.filter((b) => b.status === status);
  if (minQuantity !== null) bids = bids.filter((b) => (b.quantity ?? -Infinity) >= minQuantity);
  if (maxQuantity !== null) bids = bids.filter((b) => (b.quantity ?? Infinity) <= maxQuantity);

  return NextResponse.json({
    bids,
    totalFound: result.totalFound,
    reachable: result.reachable,
    message: result.message,
  });
}
