export interface ParsedFilters {
  keywords: string[];
  ministry: string[];
  category: string[];
  status: string | null;
  min_value: number | null;
  max_value: number | null;
  min_quantity: number | null;
  max_quantity: number | null;
}

function emptyFilters(): ParsedFilters {
  return {
    keywords: [],
    ministry: [],
    category: [],
    status: null,
    min_value: null,
    max_value: null,
    min_quantity: null,
    max_quantity: null,
  };
}

const SYSTEM_PROMPT = `You convert natural-language Indian government procurement search queries
into a strict JSON filter object. You do NOT decide which bids match - you only extract
structured filters from the user's text.

Return ONLY a JSON object with exactly these keys:
{"keywords": [], "ministry": [], "category": [], "status": null, "min_value": null, "max_value": null, "min_quantity": null, "max_quantity": null}

Rules:
- "status" must be one of: ACTIVE, CLOSED, null.
- min_value/max_value are numeric INR values. Convert "10 lakh" -> 1000000, "1 crore" -> 10000000.
- Never invent ministries or categories that are not implied by the text.
- Output valid JSON only. No markdown, no commentary, no code fences.`;

function stripCodeFences(text: string): string {
  const trimmed = text.trim();
  if (trimmed.startsWith("```")) {
    const lines = trimmed.split("\n");
    lines.shift();
    if (lines[lines.length - 1]?.trim().startsWith("```")) lines.pop();
    return lines.join("\n").trim();
  }
  return trimmed;
}

export async function parseQuery(query: string): Promise<ParsedFilters> {
  const trimmed = query.trim();
  if (!trimmed) return emptyFilters();

  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return { ...emptyFilters(), keywords: trimmed.split(/\s+/).filter((w) => w.length > 2) };
  }

  try {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
        temperature: 0,
        max_tokens: 512,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: trimmed },
        ],
      }),
    });

    if (!response.ok) throw new Error(`Groq API error: ${response.status}`);

    const data = await response.json();
    const content = data?.choices?.[0]?.message?.content;
    if (!content) throw new Error("Groq returned no content");

    const parsed = JSON.parse(stripCodeFences(content));
    const merged = emptyFilters();
    for (const key of Object.keys(merged) as (keyof ParsedFilters)[]) {
      if (key in parsed) (merged as any)[key] = parsed[key];
    }
    return merged;
  } catch {
    return { ...emptyFilters(), keywords: trimmed.split(/\s+/).filter((w) => w.length > 2) };
  }
}
