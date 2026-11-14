"use client";

import { useEffect, useRef, useState } from "react";

type Props = { src: string };

export default function GaussianWorldViewer({ src }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Preparing immersive viewer…");
  const [error, setError] = useState("");

  useEffect(() => {
    let frame = 0;
    let disposed = false;
    let renderer: import("three").WebGLRenderer | undefined;
    let controls: import("three/examples/jsm/controls/OrbitControls.js").OrbitControls | undefined;
    let scene: import("three").Scene | undefined;
    let splats: import("@sparkjsdev/spark").SplatMesh | undefined;
    let resizeObserver: ResizeObserver | undefined;

    async function load() {
      try {
        const [THREE, Spark, Controls] = await Promise.all([
          import("three"),
          import("@sparkjsdev/spark"),
          import("three/addons/controls/OrbitControls.js"),
        ]);
        if (disposed || !rootRef.current) return;

        const host = rootRef.current;
        scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(65, 1, 0.01, 1000);
        camera.position.set(0, 0, 2.5);
        renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(host.clientWidth || 800, host.clientHeight || 600);
        host.appendChild(renderer.domElement);

        const sparkRenderer = new Spark.SparkRenderer({ renderer });
        scene.add(sparkRenderer);
        controls = new Controls.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;

        splats = new Spark.SplatMesh({ url: src });
        splats.quaternion.set(1, 0, 0, 0);
        scene.add(splats);
        setStatus("Loading 3D scene…");

        resizeObserver = new ResizeObserver(() => {
          if (!renderer || !rootRef.current) return;
          const width = Math.max(1, rootRef.current.clientWidth);
          const height = Math.max(1, rootRef.current.clientHeight);
          camera.aspect = width / height;
          camera.updateProjectionMatrix();
          renderer.setSize(width, height);
        });
        resizeObserver.observe(host);

        const animate = () => {
          if (disposed || !renderer || !scene) return;
          frame = window.requestAnimationFrame(animate);
          controls?.update();
          renderer.render(scene, camera);
        };
        animate();
        setStatus("World viewer ready · drag to look around, scroll to zoom");
      } catch (err) {
        if (!disposed) setError(err instanceof Error ? err.message : "Could not initialize the 3D viewer.");
      }
    }

    void load();
    return () => {
      disposed = true;
      window.cancelAnimationFrame(frame);
      resizeObserver?.disconnect();
      controls?.dispose();
      if (splats && scene) scene.remove(splats);
      renderer?.setAnimationLoop(null);
      renderer?.dispose();
      renderer?.domElement.remove();
    };
  }, [src]);

  return <div className="relative h-full min-h-[65vh] w-full overflow-hidden rounded-3xl border border-white/10 bg-[#050b13]">
    <div ref={rootRef} className="absolute inset-0" />
    <div className="pointer-events-none absolute left-4 top-4 rounded-full border border-white/10 bg-black/50 px-4 py-2 text-xs text-white/80">{error ? "Viewer issue" : status}</div>
    {error && <div role="alert" className="absolute inset-x-5 bottom-5 rounded-xl bg-red-950/90 p-4 text-sm text-red-100">{error}</div>}
  </div>;
}
