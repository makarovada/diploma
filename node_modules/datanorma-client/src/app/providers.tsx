import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type PropsWithChildren, createContext, useContext, useMemo, useState } from "react";

const queryClient = new QueryClient();
const ThemeContext = createContext<{ dark: boolean; toggle: () => void }>({ dark: false, toggle: () => {} });

export function AppProviders({ children }: PropsWithChildren) {
  const [dark, setDark] = useState(false);
  const value = useMemo(() => ({ dark, toggle: () => setDark((d) => !d) }), [dark]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeContext.Provider value={value}>
        <div className={dark ? "dark" : ""}>{children}</div>
      </ThemeContext.Provider>
    </QueryClientProvider>
  );
}

export const useTheme = () => useContext(ThemeContext);
