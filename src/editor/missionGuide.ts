export interface MissionGuideSection {
  id: string;
  title: string;
  content: string;
  searchText: string;
  summary: string;
}

export function parseMissionGuideSections(markdown: string): MissionGuideSection[] {
  const lines = markdown.split("\n");
  const sections: MissionGuideSection[] = [];
  let currentTitle: string | null = null;
  let currentLines: string[] = [];

  const flush = () => {
    if (!currentTitle || shouldIgnoreSection(currentTitle)) {
      currentLines = [];
      return;
    }

    const content = sanitizeSectionContent(currentLines);
    if (!content) {
      currentLines = [];
      return;
    }

    sections.push({
      id: `${sections.length + 1}-${slugify(currentTitle)}`,
      title: currentTitle,
      content,
      summary: extractSummary(content),
      searchText: `${currentTitle}\n${content}`.toLowerCase(),
    });

    currentLines = [];
  };

  for (const line of lines) {
    if (line.startsWith("## ")) {
      flush();
      currentTitle = line.replace(/^##\s+/, "").trim();
      continue;
    }
    if (currentTitle) {
      currentLines.push(line);
    }
  }

  flush();
  return sections;
}

function shouldIgnoreSection(title: string) {
  return [
    /^前言：受够了天书/, 
    /^作者[:：]/,
    /^这个作品属于互联网$/,
    /^自定义任务制作完全教程 - 序章/, 
  ].some((pattern) => pattern.test(title.trim()));
}

function sanitizeSectionContent(lines: string[]) {
  return lines
    .filter((line) => !shouldIgnoreLine(line))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function shouldIgnoreLine(line: string) {
  const text = line.trim();
  if (!text) {
    return false;
  }

  return [
    /^以下内容必须打前置后/, 
    /^好了避免完瞎子了/, 
    /^↑哈哈这也是ai写的/, 
    /^作者无所谓是谁/, 
  ].some((pattern) => pattern.test(text));
}

function extractSummary(content: string) {
  const paragraphs = content
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.replace(/^[#>*\-\s]+/gm, " ").replace(/`/g, "").replace(/\s+/g, " ").trim())
    .filter(Boolean);

  if (paragraphs.length === 0) {
    return "打开章节查看详细内容。";
  }

  const text = paragraphs[0];
  return text.length > 72 ? `${text.slice(0, 72)}…` : text;
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "") || "section";
}

export function joinPath(base: string, name: string) {
  const normalizedBase = base.replace(/[\\/]+$/, "");
  return `${normalizedBase}\\${name}`;
}

export function dirname(path: string) {
  const normalized = path.replace(/[\\/]+$/, "");
  const parts = normalized.split(/[\\/]/);
  if (parts.length <= 1) {
    return normalized;
  }
  if (/^[A-Za-z]:$/.test(parts[0]) && parts.length === 2) {
    return `${parts[0]}\\`;
  }
  return parts.slice(0, -1).join("\\") || normalized;
}

export function basename(path: string) {
  return path.split(/[\\/]/).pop() || path;
}

export function isRootPath(path: string) {
  return /^[A-Za-z]:\\?$/.test(path.trim());
}