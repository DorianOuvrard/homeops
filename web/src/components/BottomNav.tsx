import { NavLink } from "react-router-dom";

function HomeIcon({ filled }: { filled?: boolean }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M3 12l9-9 9 9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 10v10h4v-6h6v6h4V10" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChatIcon({ filled }: { filled?: boolean }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z" />
        <path d="M7 9h10v2H7zm0-3h10v2H7z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8 9h8M8 13h4" strokeLinecap="round" />
    </svg>
  );
}

function FilesIcon({ filled }: { filled?: boolean }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-2 10H6v-2h12v2zm0-4H6v-2h12v2z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2v11z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function BottomNav() {
  return (
    <nav className="bg-white/80 backdrop-blur border-t border-gray-200 pb-safe shrink-0">
      <div className="flex justify-around items-center py-2 px-4">
        <NavLink to="/scan" className="flex flex-col items-center gap-0.5">
          {({ isActive }) => (
            <div className={`flex flex-col items-center gap-0.5 ${isActive ? "text-[#1a237e]" : "text-gray-400"}`}>
              <HomeIcon filled={isActive} />
              <span className="text-[10px] font-medium">ACCUEIL</span>
            </div>
          )}
        </NavLink>
        <NavLink to="/chat" className="flex flex-col items-center gap-0.5">
          {({ isActive }) => (
            isActive ? (
              <div className="bg-[#e8eaf6] rounded-2xl px-5 py-1.5 flex flex-col items-center gap-0.5 text-[#1a237e]">
                <ChatIcon filled />
                <span className="text-[10px] font-bold">CHAT</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-0.5 text-gray-400">
                <ChatIcon filled={false} />
                <span className="text-[10px] font-medium">CHAT</span>
              </div>
            )
          )}
        </NavLink>
        <NavLink to="/settings" className="flex flex-col items-center gap-0.5">
          {({ isActive }) => (
            <div className={`flex flex-col items-center gap-0.5 ${isActive ? "text-[#1a237e]" : "text-gray-400"}`}>
              <FilesIcon filled={isActive} />
              <span className="text-[10px] font-medium">FICHIERS</span>
            </div>
          )}
        </NavLink>
      </div>
    </nav>
  );
}
