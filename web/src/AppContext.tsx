import { createContext, useCallback, useContext, useState } from "react";

interface AppContextValue {
  maintenanceBadge: number;
  setMaintenanceBadge: (count: number) => void;
  pendingChatMessage: string | null;
  setPendingChatMessage: (msg: string | null) => void;
}

const AppContext = createContext<AppContextValue>({
  maintenanceBadge: 0,
  setMaintenanceBadge: () => {},
  pendingChatMessage: null,
  setPendingChatMessage: () => {},
});

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [maintenanceBadge, setMaintenanceBadge] = useState(0);
  const [pendingChatMessage, setPendingChatMessage] = useState<string | null>(null);

  const setBadge = useCallback((n: number) => setMaintenanceBadge(n), []);
  const setPending = useCallback((msg: string | null) => setPendingChatMessage(msg), []);

  return (
    <AppContext.Provider
      value={{
        maintenanceBadge,
        setMaintenanceBadge: setBadge,
        pendingChatMessage,
        setPendingChatMessage: setPending,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  return useContext(AppContext);
}
