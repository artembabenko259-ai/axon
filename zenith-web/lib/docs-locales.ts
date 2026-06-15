import type { DocsLang, DocsLocale } from "@/lib/docs-types";
import en from "@/locales/en.json";
import ru from "@/locales/ru.json";
import ua from "@/locales/ua.json";

const locales: Record<DocsLang, DocsLocale> = {
  en: en as DocsLocale,
  ru: ru as DocsLocale,
  ua: ua as DocsLocale,
};

export const DOCS_LANGS: DocsLang[] = ["en", "ru", "ua"];

export const DOCS_LANG_LABELS: Record<DocsLang, string> = {
  en: "EN",
  ru: "RU",
  ua: "UA",
};

export function getDocsLocale(lang: DocsLang): DocsLocale {
  return locales[lang] ?? locales.en;
}
