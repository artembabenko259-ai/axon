export type SkillsMasteryLang = "en" | "ru" | "ua";

export interface SkillsMasteryTocItem {
  id: string;
  label: string;
}

export interface SkillsMasteryBeforeAfter {
  before: { title: string; content: string };
  after: { title: string; content: string };
}

export interface SkillsMasteryProTip {
  title: string;
  body: string;
}

export interface SkillsMasteryStep {
  step: string;
  title: string;
  body: string;
}

export interface SkillsMasteryTableRow {
  cells: string[];
}

export interface SkillsMasterySection {
  id: string;
  eyebrow: string;
  title: string;
  lead: string;
  paragraphs?: string[];
  beforeAfter?: SkillsMasteryBeforeAfter;
  proTip?: SkillsMasteryProTip;
  designPrinciple?: { label: string; body: string };
  intro?: string;
  codePanels?: { label: string; codeKey: string }[];
  subsectionTitle?: string;
  cards?: { title: string; body: string }[];
  steps?: SkillsMasteryStep[];
  ioTable?: {
    title: string;
    headers: string[];
    rows: SkillsMasteryTableRow[];
  };
  pipingTableMarkdown?: string;
  pipingMentalModelTitle?: string;
  multiStepTitle?: string;
  multiStepIntro?: string;
  troubleshootingRows?: SkillsMasteryTableRow[];
  templateLabel?: string;
  sandbox?: {
    title: string;
    placeholder: string;
    initial: string;
    scenarios: Record<string, string>;
    footer: string;
  };
}

export interface SkillsMasteryLocale {
  meta: {
    pageTitle: string;
    moduleLabel: string;
    title: string;
    lead: string;
    badge: string;
    tocTitle: string;
    backToBible: string;
  };
  labels: {
    proTip: string;
    before: string;
    after: string;
    troubleshootingHeaders: string[];
  };
  toc: SkillsMasteryTocItem[];
  code: Record<string, string>;
  sections: SkillsMasterySection[];
}
