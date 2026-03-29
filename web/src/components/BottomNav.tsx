import { NavLink } from "react-router-dom";
import { useAppContext } from "../AppContext";

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
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MaintenanceIcon({ filled }: { filled?: boolean }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function BranIcon({ filled }: { filled?: boolean }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function ProfileIcon({ filled }: { filled?: boolean }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-6 h-6">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

export default function BottomNav() {
  const { maintenanceBadge } = useAppContext();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center gap-0.5 text-[10px] font-medium transition-colors ${
      isActive ? "text-[#c45d3e]" : "text-gray-400"
    }`;

  return (
    <nav className="bg-white border-t border-[#f0ece7] pb-safe shrink-0">
      <div className="flex justify-around items-center py-2 px-4">
        <NavLink to="/scan" className={linkClass}>
          {({ isActive }) => (
            <>
              <HomeIcon filled={isActive} />
              <span>MAISON</span>
            </>
          )}
        </NavLink>
        <NavLink to="/chat" className={linkClass}>
          {({ isActive }) => (
            <>
              <ChatIcon filled={isActive} />
              <span>CHAT</span>
            </>
          )}
        </NavLink>
        <NavLink to="/maintenance" className={linkClass}>
          {({ isActive }) => (
            <>
              <div className="relative">
                <MaintenanceIcon filled={isActive} />
                {maintenanceBadge > 0 && (
                  <span className="absolute -top-1 -right-2 bg-[#c45d3e] text-white text-[9px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                    {maintenanceBadge > 9 ? "9+" : maintenanceBadge}
                  </span>
                )}
              </div>
              <span>ENTRETIEN</span>
            </>
          )}
        </NavLink>
        <NavLink to="/bran" className={linkClass}>
          {({ isActive }) => (
            <>
              <BranIcon filled={isActive} />
              <span>CONNECT</span>
            </>
          )}
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          {({ isActive }) => (
            <>
              <ProfileIcon filled={isActive} />
              <span>PROFIL</span>
            </>
          )}
        </NavLink>
      </div>
    </nav>
  );
}
