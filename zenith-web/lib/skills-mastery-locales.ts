import type { SkillsMasteryLang, SkillsMasteryLocale } from "@/lib/skills-mastery-types";
import en from "@/locales/skills-mastery/en.json";
import ru from "@/locales/skills-mastery/ru.json";
import ua from "@/locales/skills-mastery/ua.json";

const locales: Record<SkillsMasteryLang, SkillsMasteryLocale> = {
  en: en as SkillsMasteryLocale,
  ru: ru as SkillsMasteryLocale,
  ua: ua as SkillsMasteryLocale,
};

export function getSkillsMasteryLocale(
  lang: SkillsMasteryLang,
): SkillsMasteryLocale {
  return locales[lang] ?? locales.en;
}
