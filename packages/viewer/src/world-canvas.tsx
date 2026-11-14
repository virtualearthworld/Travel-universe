"use client";
import { Canvas } from "@react-three/fiber";
function PlaceholderWorld() { return <mesh rotation={[0.35, 0.5, 0]}><icosahedronGeometry args={[1, 2]} /><meshStandardMaterial color="#54d6c8" wireframe /></mesh>; }
/** Renderer smoke-test scene. Gaussian Splat loading is scheduled for Phase 4. */
export function WorldCanvas() { return <div className="h-72 w-full overflow-hidden rounded-2xl bg-slate-950"><Canvas camera={{ position: [0, 0, 3.5], fov: 50 }}><ambientLight intensity={0.8} /><directionalLight position={[3, 4, 5]} intensity={1.5} /><PlaceholderWorld /></Canvas></div>; }
