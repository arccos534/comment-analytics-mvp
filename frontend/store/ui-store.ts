import { create } from "zustand";

interface UiState {
  latestAnalysisRunId: string | null;
  setLatestAnalysisRunId: (value: string | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  latestAnalysisRunId: null,
  setLatestAnalysisRunId: (value) => set({ latestAnalysisRunId: value })
}));
