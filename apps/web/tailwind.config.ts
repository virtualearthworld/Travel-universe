import type { Config } from "tailwindcss";
const config: Config = { content: ["./src/**/*.{ts,tsx}", "../../packages/viewer/src/**/*.{ts,tsx}"], theme: { extend: { colors: { midnight: "#07111f", ocean: "#0b2545", aqua: "#54d6c8", sand: "#f3ead8" } } }, plugins: [] };
export default config;
