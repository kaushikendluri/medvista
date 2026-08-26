"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Types } from "@cornerstonejs/core";
import {
  RENDERING_ENGINE_ID,
  ensureCornerstoneInitialized,
  getOrCreateToolGroup,
  voiRangeFromWindow,
} from "@/lib/cornerstone-viewer";

const VIEWPORT_ID = "medvista-stack-viewport";

export interface PersistedAnnotationPayload {
  toolName: string;
  kind: "measurement" | "annotation";
  value?: number;
  unit?: string;
  label?: string;
  geometry: unknown;
}

export interface DicomViewportHandle {
  reset: () => void;
  toggleInvert: () => void;
  applyWindowLevel: (windowWidth: number, windowCenter: number) => void;
  goToIndex: (index: number) => void;
}

interface Props {
  imageIds: string[];
  onIndexChange?: (index: number, total: number) => void;
  onAnnotationCompleted?: (payload: PersistedAnnotationPayload) => void;
  onError?: (message: string) => void;
}

export const DicomViewport = forwardRef<DicomViewportHandle, Props>(function DicomViewport(
  { imageIds, onIndexChange, onAnnotationCompleted, onError },
  ref,
) {
  const elementRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<Types.IStackViewport | null>(null);
  const [ready, setReady] = useState(false);

  useImperativeHandle(ref, () => ({
    reset: () => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      viewport.resetCamera();
      viewport.resetProperties();
      viewport.render();
    },
    toggleInvert: () => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      const current = viewport.getProperties();
      viewport.setProperties({ invert: !current.invert });
      viewport.render();
    },
    applyWindowLevel: (windowWidth: number, windowCenter: number) => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      viewport.setProperties({ voiRange: voiRangeFromWindow(windowWidth, windowCenter) });
      viewport.render();
    },
    goToIndex: (index: number) => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      viewport.setImageIdIndex(index);
    },
  }));

  useEffect(() => {
    if (imageIds.length === 0) return;
    let cancelled = false;

    (async () => {
      try {
        await ensureCornerstoneInitialized();
        if (cancelled || !elementRef.current) return;

        const core = await import("@cornerstonejs/core");
        const cornerstoneTools = await import("@cornerstonejs/tools");

        let renderingEngine = core.getRenderingEngine(RENDERING_ENGINE_ID);
        if (!renderingEngine) {
          renderingEngine = new core.RenderingEngine(RENDERING_ENGINE_ID);
        }

        renderingEngine.enableElement({
          viewportId: VIEWPORT_ID,
          type: core.Enums.ViewportType.STACK,
          element: elementRef.current,
        });

        const viewport = renderingEngine.getViewport(VIEWPORT_ID) as Types.IStackViewport;
        viewportRef.current = viewport;

        const toolGroup = getOrCreateToolGroup();
        toolGroup.addViewport(VIEWPORT_ID, RENDERING_ENGINE_ID);

        await viewport.setStack(imageIds, 0);
        viewport.render();
        if (cancelled) return;
        setReady(true);
        onIndexChange?.(0, imageIds.length);

        const element = elementRef.current;
        const handleStackScroll = () => {
          const idx = viewport.getCurrentImageIdIndex();
          onIndexChange?.(idx, imageIds.length);
        };
        element.addEventListener(core.Enums.Events.STACK_NEW_IMAGE, handleStackScroll);

        const handleAnnotationCompleted = (evt: Event) => {
          const detail = (evt as CustomEvent).detail as {
            annotation: {
              metadata: { toolName: string };
              data: { handles?: { points: unknown }; text?: string; cachedStats?: Record<string, unknown> };
            };
          };
          const annotation = detail.annotation;
          const toolName = annotation.metadata.toolName;

          if (toolName === cornerstoneTools.LengthTool.toolName) {
            const stats = Object.values(annotation.data.cachedStats ?? {})[0] as
              | { length?: number; unit?: string }
              | undefined;
            onAnnotationCompleted?.({
              toolName,
              kind: "measurement",
              value: stats?.length,
              unit: stats?.unit ?? "mm",
              geometry: { points: annotation.data.handles?.points },
            });
          } else if (toolName === cornerstoneTools.ArrowAnnotateTool.toolName) {
            onAnnotationCompleted?.({
              toolName,
              kind: "annotation",
              label: annotation.data.text,
              geometry: { points: annotation.data.handles?.points },
            });
          }
        };
        element.addEventListener(
          cornerstoneTools.Enums.Events.ANNOTATION_COMPLETED,
          handleAnnotationCompleted,
        );

        return () => {
          element.removeEventListener(core.Enums.Events.STACK_NEW_IMAGE, handleStackScroll);
          element.removeEventListener(
            cornerstoneTools.Enums.Events.ANNOTATION_COMPLETED,
            handleAnnotationCompleted,
          );
        };
      } catch (err) {
        console.error("Cornerstone viewport failed to initialize", err);
        onError?.(err instanceof Error ? err.message : "Failed to load imaging viewer");
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageIds.join("|")]);

  useEffect(() => {
    return () => {
      import("@cornerstonejs/core").then(({ getRenderingEngine }) => {
        getRenderingEngine(RENDERING_ENGINE_ID)?.destroy();
      });
    };
  }, []);

  return (
    <div className="relative h-full w-full">
      <div ref={elementRef} className="h-full w-full bg-black" />
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">
          Loading imaging viewer…
        </div>
      )}
    </div>
  );
});
