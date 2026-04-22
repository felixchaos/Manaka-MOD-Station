const missionPropertyKeywords = [
  "title",
  "version",
  "author",
  "zones",
  "id",
  "areas",
  "stage",
  "x",
  "y",
  "z",
  "r",
  "subconditions",
  "checkpoints",
  "condition",
  "description",
  "duration",
  "oncomplete",
  "travelcondition",
  "zoneId",
  "type",
  "goto",
  "target",
  "value",
  "enabled",
];

const missionStageValues = [
  "Park",
  "Mall",
  "Convenience",
  "Apartment",
  "Residential",
  "Downtown",
  "Shop",
  "Alley",
];

let isConfigured = false;

export function configureSerikaMissionMonaco(monaco: any) {
  if (isConfigured) {
    return;
  }
  isConfigured = true;

  monaco.languages.register({ id: "serikaMission" });

  monaco.languages.setMonarchTokensProvider("serikaMission", {
    defaultToken: "",
    tokenizer: {
      root: [
        [/\s+/, "white"],
        [/\{/, "delimiter.bracket"],
        [/\}/, "delimiter.bracket"],
        [/\[/, "delimiter.array"],
        [/\]/, "delimiter.array"],
        [/,/, "delimiter"],
        [/:/, "delimiter"],
        [/-?\d*\.\d+([eE][\-+]?\d+)?/, "number.float"],
        [/-?\d+/, "number"],
        [/\b(?:true|false|null)\b/, "keyword"],
        [new RegExp(`\"(?:${missionPropertyKeywords.join("|")})\"(?=\\s*:)`), "keyword"],
        [new RegExp(`\"(?:${missionStageValues.join("|")})\"`), "type.identifier"],
        [/"\[(?:Action|Stage|State|Pose|Item|Event|Condition|Target|Area)_[^"]*\]"/, "regexp"],
        [/"(?:goto|teleport|equip|unequip|setCheckpoint|random|branch|loop)"/, "predefined"],
        [/"([^"\\]|\\.)*"/, "string"],
      ],
    },
  });

  monaco.languages.setLanguageConfiguration("serikaMission", {
    brackets: [
      ["{", "}"],
      ["[", "]"],
      ["(", ")"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
    ],
    surroundingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
    ],
  });

  monaco.editor.defineTheme("serika-mission-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "7CB7FF", fontStyle: "bold" },
      { token: "string", foreground: "D7BA7D" },
      { token: "number", foreground: "B5CEA8" },
      { token: "number.float", foreground: "9CDCFE" },
      { token: "type.identifier", foreground: "4EC9B0", fontStyle: "bold" },
      { token: "regexp", foreground: "C586C0" },
      { token: "predefined", foreground: "DCDCAA", fontStyle: "bold" },
      { token: "delimiter.array", foreground: "D4D4D4" },
      { token: "delimiter.bracket", foreground: "D4D4D4" },
    ],
    colors: {
      "editor.background": "#1B1B1F",
      "editor.lineHighlightBackground": "#24242A",
      "editorLineNumber.foreground": "#6B7280",
      "editorLineNumber.activeForeground": "#D1D5DB",
      "editorCursor.foreground": "#F9FAFB",
      "editor.selectionBackground": "#264F78",
    },
  });

  monaco.editor.defineTheme("serika-mission-light", {
    base: "vs",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "0F4C81", fontStyle: "bold" },
      { token: "string", foreground: "A31515" },
      { token: "number", foreground: "098658" },
      { token: "number.float", foreground: "0451A5" },
      { token: "type.identifier", foreground: "0B6E4F", fontStyle: "bold" },
      { token: "regexp", foreground: "AF00DB" },
      { token: "predefined", foreground: "795E26", fontStyle: "bold" },
    ],
    colors: {
      "editor.background": "#FCFCFD",
      "editor.lineHighlightBackground": "#F3F4F6",
      "editorLineNumber.foreground": "#9CA3AF",
      "editorLineNumber.activeForeground": "#111827",
      "editorCursor.foreground": "#111827",
      "editor.selectionBackground": "#CFE8FF",
    },
  });
}