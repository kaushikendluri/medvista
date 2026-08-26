"use client";

import clsx from "clsx";
import { WINDOW_LEVEL_PRESETS, type ToolKey } from "@/lib/cornerstone-viewer";

const TOOL_BUTTONS: { key: ToolKey; label: string }[] = [
  { key: "WindowLevel", label: "Window/Level" },
  { key: "Zoom", label: "Zoom" },
  { key: "Pan", label: "Pan" },
  { key: "Length", label: "Measure" },
  { key: "ArrowAnnotate", label: "Annotate" },
];

export function ViewerToolbar({
  activeTool,
  onToolChange,
  onPreset,
  onReset,
  onInvert,
}: {
  activeTool: ToolKey;
  onToolChange: (tool: ToolKey) => void;
  onPreset: (windowWidth: number, windowCenter: number) => void;
  onReset: () => void;
  onInvert: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-base-700/60 bg-base-900/40 px-4 py-2">
      <div className="flex items-center gap-1">
        {TOOL_BUTTONS.map((tool) => (
          <button
            key={tool.key}
            onClick={() => onToolChange(tool.key)}
            className={clsx(
              "focus-ring rounded-md px-2.5 py-1.5 text-xs transition",
              activeTool === tool.key
                ? "bg-accent/15 text-accent"
                : "text-slate-400 hover:bg-base-800 hover:text-slate-200",
            )}
          >
            {tool.label}
          </button>
        ))}
      </div>

      <div className="h-4 w-px bg-base-700" />

      <select
        onChange={(e) => {
          const preset = WINDOW_LEVEL_PRESETS[Number(e.target.value)];
          if (preset) onPreset(preset.windowWidth, preset.windowCenter);
        }}
        defaultValue=""
        className="focus-ring rounded-md border border-base-600 bg-base-850 px-2 py-1.5 text-xs text-slate-300"
      >
        <option value="" disabled>
          Window/Level preset
        </option>
        {WINDOW_LEVEL_PRESETS.map((preset, i) => (
          <option key={preset.label} value={i}>
            {preset.label}
          </option>
        ))}
      </select>

      <div className="h-4 w-px bg-base-700" />

      <button
        onClick={onInvert}
        className="focus-ring rounded-md px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-base-800 hover:text-slate-200"
      >
        Invert
      </button>
      <button
        onClick={onReset}
        className="focus-ring rounded-md px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-base-800 hover:text-slate-200"
      >
        Reset
      </button>
    </div>
  );
}
