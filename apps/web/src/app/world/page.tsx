"use client";

import { useState } from "react";
import Link from "next/link";
import GaussianWorldViewer from "@/components/gaussian-world-viewer";

export default function WorldPage() {
  const [src, setSrc] = useState("");
  const [active, setActive] = useState("");
  return <main className="min-h-screen bg-[#07111f] px-5 py-8 text-white">
    <div className="mx-auto max-w-7xl">
      <Link href="/" className="text-sm text-[#54d6c8]">← Travel Universe</Link>
      <p className="mt-10 text-xs font-bold tracking-[.3em] text-[#54d6c8]">ENTER A WORLD</p>
      <h1 className="mt-3 text-4xl font-semibold">Explore a reconstructed place.</h1>
      <p className="mt-4 max-w-3xl leading-7 text-white/60">Load a Gaussian Splat scene URL to explore it with the browser viewer. The Spark renderer supports PLY, SPZ, SPLAT and KSPLAT scene files.</p>
      <form className="mt-7 flex flex-col gap-3 sm:flex-row" onSubmit={e => { e.preventDefault(); setActive(src.trim()); }}>
        <input aria-label="3D scene URL" value={src} onChange={e => setSrc(e.target.value)} placeholder="https://…/your-scene.ply" className="min-w-0 flex-1 rounded-full border border-white/15 bg-white/[.06] px-5 py-3 text-sm outline-none focus:border-[#54d6c8]" />
        <button type="submit" disabled={!src.trim()} className="rounded-full bg-[#54d6c8] px-7 py-3 font-semibold text-[#07111f] disabled:opacity-40">Load world</button>
      </form>
      <div className="mt-7">
        {active ? <GaussianWorldViewer key={active} src={active} /> : <div className="flex min-h-[65vh] items-center justify-center rounded-3xl border border-dashed border-white/15 bg-white/[.025] p-8 text-center"><div><p className="text-xl font-semibold">Your 3D destination will appear here</p><p className="mt-3 text-sm text-white/50">Paste a supported scene URL above to enter it</p></div></div>}
      </div>
      <p className="mt-5 text-xs leading-6 text-white/35">Only load scene files from sources you trust. Scene files must be hosted with browser-accessible CORS headers. Shared-memory mode is disabled for broader local compatibility.</p>
    </div>
  </main>;
}
