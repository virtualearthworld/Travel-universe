import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Travel Universe", description: "Discover places. Enter worlds. Share the journey." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
