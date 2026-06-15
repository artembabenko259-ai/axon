import {
  transformOpenRouterModels,
  type OpenRouterModelsResponse,
} from "@/lib/models";

export const revalidate = 3600;

export async function GET() {
  try {
    const response = await fetch("https://openrouter.ai/api/v1/models", {
      headers: {
        "HTTP-Referer": process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
        "X-Title": "AXON Model Marketplace",
      },
      next: { revalidate: 3600 },
    });

    if (!response.ok) {
      return Response.json(
        { error: `OpenRouter API error: ${response.status}` },
        { status: response.status },
      );
    }

    const json = (await response.json()) as OpenRouterModelsResponse;
    const models = transformOpenRouterModels(json.data ?? []);

    return Response.json({ models, fetchedAt: new Date().toISOString() });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to fetch models";
    return Response.json({ error: message }, { status: 500 });
  }
}
