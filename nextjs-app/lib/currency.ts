const LAKH = 100_000;
const CRORE = 10_000_000;

const UNIT_MULTIPLIERS: Record<string, number> = {
  crore: CRORE,
  crores: CRORE,
  cr: CRORE,
  lakh: LAKH,
  lakhs: LAKH,
  lac: LAKH,
  lacs: LAKH,
};

const NUMBER_UNIT_RE = /([\d,]+(?:\.\d+)?)\s*(crore|crores|cr|lakh|lakhs|lac|lacs)?/i;

export function parseInr(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return value;

  let text = value.replace(/₹|Rs\.?|INR/gi, "").trim();
  const match = NUMBER_UNIT_RE.exec(text);
  if (!match) return null;

  const num = parseFloat(match[1].replace(/,/g, ""));
  if (Number.isNaN(num)) return null;

  const unit = match[2]?.toLowerCase();
  const multiplier = unit ? UNIT_MULTIPLIERS[unit] ?? 1 : 1;
  return num * multiplier;
}

export function formatInr(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  if (value >= CRORE) return `₹${(value / CRORE).toFixed(2)} crore`;
  if (value >= LAKH) return `₹${(value / LAKH).toFixed(2)} lakh`;
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}
