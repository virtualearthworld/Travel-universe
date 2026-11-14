"use client";

import { useEffect, useRef, useState } from "react";

type Props = { src: string };

export default function GaussianWorldViewer({ src }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Preparing 3D viewer…");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let viewer: import("@mkkellogg/gaussian-splats-3d").Viewer | undefined;
    async function load() {
      const extension = src.split("?")[0].split(".").pop()?.toLowerCase();
      if (!["ply", "splat", "ksplat"].includes(extension || "")) {
        setError("This viewer currently accepts .ply, .splat, or .ksplat scenes. Convert .spz to a supported format before loading.");
        return;
      }
      try {
        const module = await import("@mkkellogg/gaussian-splats-3d");
        if (cancelled || !rootRef.current) return;
        viewer = new module.Viewer({
          rootElement: rootRef.current,
          sharedMemoryForWorkers: false,
          gpuAcceleratedSort: false,
          initialCameraPosition: [0, 1, 5],
          initialCameraLookAt: [0, 0, 0],
          cameraUp: [0, 1, 0],
        });
        setStatus("Loading scene…");
        await viewer.addSplatScene(src, { showLoadingUI: false, progressiveLoad: true });
        if (cancelled) return;
        viewer.start();
        setStatus("World loaded · drag to look around");
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load this 3D scene.");
      }
    }
    void load();
    return () => {
      cancelled = true;
      if (viewer) void viewer.dispose().catch(() => undefined);
    };
  }, [src]);

  return <div className="relative h-full min-h-[65vh] w-full overflow-hidden rounded-3xl border border-white/10 bg-[#050b13]">
    <div ref={rootRef} className="absolute inset-0" />
    <div className="pointer-events-none absolute left-4 top-4 rounded-full border border-white/10 bg-black/50 px-4 py-2 text-xs text-white/80">{error ? "Viewer issue" : status}</div>
    {error && <div role="alert" className="absolute inset-x-5 bottom-5 rounded-xl bg-red-950/90 p-4 text-sm text-red-100">{error}</div>}
  </div>;
}
