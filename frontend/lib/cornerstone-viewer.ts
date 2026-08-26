"use client";

/**
 * Client-only Cornerstone3D bootstrap. Must never run during SSR — these
 * packages touch `window`/canvas/Web Workers at init time.
 *
 * Images are loaded via the `wadouri` scheme: the loader fetches the whole
 * original DICOM Part 10 file (backend GET .../instances/:id/file) and
 * parses it client-side, deriving its own metadata from the real dataset.
 * This is simpler and more robust here than wiring full DICOMweb WADO-RS
 * multipart-frame streaming against a non-standard backend.
 *
 * Known limitation: compressed transfer syntaxes (JPEG2000, JPEG-LS, etc.)
 * need the loader's WASM codecs, which are not specially configured here
 * (see DICOM.md). Uncompressed native pixel data — what our own upload
 * pipeline and test fixtures produce — decodes without them.
 */
import { init as coreInit } from "@cornerstonejs/core";
import * as cornerstoneTools from "@cornerstonejs/tools";
import { init as dicomImageLoaderInit } from "@cornerstonejs/dicom-image-loader";

export const RENDERING_ENGINE_ID = "medvista-rendering-engine";
export const TOOL_GROUP_ID = "medvista-viewer-tools";

export const TOOL_NAMES = {
  WindowLevel: cornerstoneTools.WindowLevelTool.toolName,
  Pan: cornerstoneTools.PanTool.toolName,
  Zoom: cornerstoneTools.ZoomTool.toolName,
  StackScroll: cornerstoneTools.StackScrollTool.toolName,
  Length: cornerstoneTools.LengthTool.toolName,
  ArrowAnnotate: cornerstoneTools.ArrowAnnotateTool.toolName,
} as const;

export type ToolKey = keyof typeof TOOL_NAMES;

let initPromise: Promise<void> | null = null;

export function ensureCornerstoneInitialized(): Promise<void> {
  if (!initPromise) {
    initPromise = (async () => {
      await coreInit();
      await cornerstoneTools.init();
      dicomImageLoaderInit({ maxWebWorkers: 1 });

      cornerstoneTools.addTool(cornerstoneTools.WindowLevelTool);
      cornerstoneTools.addTool(cornerstoneTools.PanTool);
      cornerstoneTools.addTool(cornerstoneTools.ZoomTool);
      cornerstoneTools.addTool(cornerstoneTools.StackScrollTool);
      cornerstoneTools.addTool(cornerstoneTools.LengthTool);
      cornerstoneTools.addTool(cornerstoneTools.ArrowAnnotateTool);
    })();
  }
  return initPromise;
}

export function getOrCreateToolGroup() {
  let toolGroup = cornerstoneTools.ToolGroupManager.getToolGroup(TOOL_GROUP_ID);
  if (!toolGroup) {
    toolGroup = cornerstoneTools.ToolGroupManager.createToolGroup(TOOL_GROUP_ID);
    if (!toolGroup) throw new Error("Unable to create Cornerstone tool group");
    for (const toolName of Object.values(TOOL_NAMES)) {
      toolGroup.addTool(toolName);
    }
    // Stack scroll is always active on the mouse wheel, independent of the
    // currently selected primary-button tool.
    toolGroup.setToolActive(TOOL_NAMES.StackScroll, {
      bindings: [{ mouseButton: cornerstoneTools.Enums.MouseBindings.Wheel }],
    });
  }
  return toolGroup;
}

export function setActivePrimaryTool(toolKey: ToolKey) {
  const toolGroup = getOrCreateToolGroup();
  const targetTool = TOOL_NAMES[toolKey];
  for (const toolName of Object.values(TOOL_NAMES)) {
    if (toolName === targetTool || toolName === TOOL_NAMES.StackScroll) continue;
    toolGroup.setToolPassive(toolName);
  }
  toolGroup.setToolActive(targetTool, {
    bindings: [{ mouseButton: cornerstoneTools.Enums.MouseBindings.Primary }],
  });
  // Pan/Zoom stay reachable with secondary/auxiliary buttons regardless of
  // the primary tool, matching conventional PACS mouse ergonomics.
  if (targetTool !== TOOL_NAMES.Pan) {
    toolGroup.setToolActive(TOOL_NAMES.Pan, {
      bindings: [{ mouseButton: cornerstoneTools.Enums.MouseBindings.Auxiliary }],
    });
  }
  if (targetTool !== TOOL_NAMES.Zoom) {
    toolGroup.setToolActive(TOOL_NAMES.Zoom, {
      bindings: [{ mouseButton: cornerstoneTools.Enums.MouseBindings.Secondary }],
    });
  }
}

export const WINDOW_LEVEL_PRESETS: { label: string; windowWidth: number; windowCenter: number }[] = [
  { label: "Soft Tissue", windowWidth: 400, windowCenter: 40 },
  { label: "Lung", windowWidth: 1500, windowCenter: -600 },
  { label: "Bone", windowWidth: 2000, windowCenter: 500 },
  { label: "Brain", windowWidth: 80, windowCenter: 40 },
];

export function voiRangeFromWindow(windowWidth: number, windowCenter: number) {
  return { lower: windowCenter - windowWidth / 2, upper: windowCenter + windowWidth / 2 };
}
