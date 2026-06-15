export type DocsLang = "en" | "ru" | "ua";

export interface DocStepRow {
  step: string;
  what: string;
  who: string;
}

export interface DocStepsTable {
  title?: string;
  headers: { step: string; what: string; who: string };
  rows: DocStepRow[];
}

export interface DocBeforeAfter {
  before: { title: string; content: string };
  after: { title: string; content: string };
}

export interface DocAnimation {
  id: string;
  title: string;
  description: string;
  trigger: string;
}

export interface DocSandbox {
  title?: string;
  placeholder: string;
  button?: string;
  initial?: string;
  scenarios: Record<string, string>;
}

export interface DocExample {
  title: string;
  markdown: string;
}

export interface DocFailureMode {
  title: string;
  markdown: string;
}

export interface DocSubsection {
  id: string;
  title: string;
  page?: number;
  eli5?: string;
  theoreticalFoundation?: string;
  markdown?: string;
  examples?: DocExample[];
  failureMode?: DocFailureMode;
  beforeAfter?: DocBeforeAfter;
  stepsTable?: DocStepsTable;
  animation?: DocAnimation;
  animations?: DocAnimation[];
  sandbox?: DocSandbox;
}

export interface DocSection {
  id: string;
  title: string;
  lead: string;
  chapter: number;
  subsections: DocSubsection[];
}

export interface DocsLocale {
  meta: {
    title: string;
    lead: string;
    bookSubtitle: string;
    totalPages?: number;
    chapterCount?: number;
    mergedFrom?: string[];
  };
  sections: DocSection[];
}
