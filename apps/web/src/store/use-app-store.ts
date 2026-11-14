"use client";
import { create } from "zustand";
type AppState = { activeDestination: string | null; setActiveDestination: (destination: string | null) => void };
export const useAppStore = create<AppState>((set) => ({ activeDestination: null, setActiveDestination: (activeDestination) => set({ activeDestination }) }));
