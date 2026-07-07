export interface OpenRouterPricing {
  prompt: string;
  completion: string;
  request?: string;
  image?: string;
}

export interface OpenRouterModel {
  id: string;
  name: string;
  description?: string;
  context_length: number;
  pricing: OpenRouterPricing;
  architecture?: {
    modality?: string;
    tokenizer?: string;
  };
}

export interface OpenRouterModelsResponse {
  data: OpenRouterModel[];
}

export type ModelCategory = "all" | "coding" | "general" | "fast";

export interface MarketplaceModel {
  id: string;
  name: string;
  provider: string;
  contextWindow: number;
  inputPricePerMillion: number;
  outputPricePerMillion: number;
  categories: ModelCategory[];
  isRecommended: boolean;
  isTrending: boolean;
}

/** Convert per-token string price to $/1M tokens. */
export function toPricePerMillion(tokenPrice: string): number {
  const perToken = parseFloat(tokenPrice);
  if (Number.isNaN(perToken)) return 0;
  return perToken * 1_000_000;
}

export function parseProvider(modelId: string): string {
  return modelId.split("/")[0] ?? "unknown";
}

export function categorizeModel(modelId: string, name: string): ModelCategory[] {
  const haystack = `${modelId} ${name}`.toLowerCase();
  const categories: ModelCategory[] = ["general"];

  if (
    /coder|code|codestral|starcoder|deepseek.*v3|qwen.*coder|devstral/i.test(
      haystack,
    )
  ) {
    categories.push("coding");
  }

  if (
    /haiku|flash|8b|7b|mini|small|lite|fast|instant|turbo|nano/i.test(haystack)
  ) {
    categories.push("fast");
  }

  return categories;
}

export function transformOpenRouterModels(
  models: OpenRouterModel[],
): MarketplaceModel[] {
  const transformed = models
    .filter((m) => m.pricing?.prompt && m.pricing?.completion)
    .map((m) => {
      const inputPrice = toPricePerMillion(m.pricing.prompt);
      const outputPrice = toPricePerMillion(m.pricing.completion);
      const categories = categorizeModel(m.id, m.name);

      return {
        id: m.id,
        name: m.name,
        provider: parseProvider(m.id),
        contextWindow: m.context_length ?? 0,
        inputPricePerMillion: inputPrice,
        outputPricePerMillion: outputPrice,
        categories,
        isRecommended: false,
        isTrending: false,
      };
    })
    .sort((a, b) => a.inputPricePerMillion - b.inputPricePerMillion);

  const prices = transformed.map(
    (m) => m.inputPricePerMillion + m.outputPricePerMillion,
  );
  const sortedPrices = [...prices].sort((a, b) => a - b);
  const cheapThreshold =
    sortedPrices[Math.floor(sortedPrices.length * 0.15)] ?? 0;

  const trendingIds = new Set(
    ["meta-llama/llama-3.1-8b-instruct", "qwen/qwen-2.5-coder-32b-instruct", "openai/gpt-4o-mini", "anthropic/claude-3-haiku"].filter(Boolean),
  );

  return transformed.map((m) => {
    const total = m.inputPricePerMillion + m.outputPricePerMillion;
    return {
      ...m,
      isRecommended: total <= cheapThreshold && total > 0,
      isTrending: trendingIds.has(m.id),
    };
  });
}

export function formatPrice(value: number): string {
  if (value < 0) return "—";
  if (value === 0) return "Free";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

export function formatContext(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K`;
  return String(tokens);
}
