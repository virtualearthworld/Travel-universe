"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Job = { job_id: string; status: string; progress?: { stage?: string; percent?: number }; result?: { status?: string; duration_seconds?: string; frame_count?: string; next_step?: string }; error?: string };
const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [message, setMessage] = useState("");
  const [videoId, setVideoId] = useState("");

  useEffect(() => {
    if (!API || !job?.job_id || ["success", "failure"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API}/api/v1/jobs/${job.job_id}`);
        if (!response.ok) return;
        const next = (await response.json()) as Job;
        setJob(next);
      } catch {
        setMessage("Cannot reach the video-processing service. Please try again later.");
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [job?.job_id, job?.status]);

  async function submit() {
    if (!file) return;
    if (!API) {
      setMessage("The Travel Universe website preview is online. Video processing is not connected yet; the upload service must be deployed before videos can be analyzed.");
      return;
    }
    setBusy(true); setMessage(""); setJob(null);
    try {
      const body = new FormData(); body.append("file", file);
      const response = await fetch(`${API}/api/v1/videos/upload`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed.");
      setVideoId(data.video_id);
      setJob({ job_id: data.job_id, status: "pending" });
      setMessage("Upload complete. Your video is in the processing queue.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong.");
    } finally { setBusy(false); }
  }

  const percent = job?.progress?.percent ?? (job?.status === "success" ? 100 : 0);
  return <main className="min-h-screen bg-[#07111f] px-5 py-10 text-white">
    <div className="mx-auto max-w-3xl">
      <Link href="/" className="text-sm text-[#54d6c8]">← Travel Universe</Link>
      <p className="mt-12 text-xs font-bold tracking-[.3em] text-[#54d6c8]">CREATE A WORLD</p>
      <h1 className="mt-4 text-4xl font-semibold sm:text-5xl">Bring your travel video.</h1>
      <p className="mt-5 max-w-2xl leading-7 text-white/60">Upload an MP4, MOV, or WebM clip (up to 500 MB and 10 minutes). The system stores it, validates the footage, and extracts frames for the 3D reconstruction stage.</p>
      <section className="mt-10 rounded-3xl border border-white/10 bg-white/[.04] p-7">
        <label htmlFor="video" className="block text-sm font-medium">Choose a travel video</label>
        <input id="video" type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" onChange={e => { setFile(e.target.files?.[0] ?? null); setJob(null); setVideoId(""); setMessage(""); }} className="mt-4 block w-full rounded-xl border border-white/15 bg-black/20 p-4 text-sm file:mr-4 file:rounded-full file:border-0 file:bg-[#54d6c8] file:px-4 file:py-2 file:font-semibold file:text-[#07111f]" />
        {file && <p className="mt-3 text-xs text-white/50">{file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB</p>}
        <button onClick={submit} disabled={!file || busy} className="mt-6 rounded-full bg-[#54d6c8] px-7 py-3 font-semibold text-[#07111f] disabled:cursor-not-allowed disabled:opacity-40">{busy ? "Uploading…" : "Upload and analyze"}</button>
        {message && <p role="status" className="mt-5 text-sm text-white/75">{message}</p>}
      </section>
      {job && <section className="mt-6 rounded-3xl border border-white/10 bg-white/[.04] p-7">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold">Processing status</h2><span className="rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-wider">{job.status}</span></div>
        <p className="mt-3 text-sm text-white/55">{job.progress?.stage?.replaceAll("_", " ") || "Waiting for worker"}</p>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-[#54d6c8] transition-all" style={{ width: `${percent}%` }} /></div>
        {job.result && <div className="mt-5 space-y-2 text-sm text-white/70"><p>Video duration: {job.result.duration_seconds}s</p><p>Frames extracted: {job.result.frame_count}</p><p className="mt-4 leading-6 text-[#f4c77b]">{job.result.next_step}</p></div>}
        {job.error && <p className="mt-4 text-sm text-red-300">{job.error}</p>}
        <p className="mt-5 break-all text-xs text-white/35">Video ID: {videoId} · Job ID: {job.job_id}</p>
      </section>}
      <p className="mt-8 text-xs leading-6 text-white/35">The current pipeline prepares video frames. A GPU-enabled Gaussian Splatting trainer and scene exporter are still required to create the final explorable 3D world.</p>
    </div>
  </main>;
}
