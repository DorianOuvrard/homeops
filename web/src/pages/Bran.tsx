import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, type BranDevice, type BranStatus } from "../api";

type Phase = "idle" | "scanning" | "revealing" | "done" | "error" | "empty";

export default function Bran() {
  const [status, setStatus] = useState<BranStatus | null>(null);
  const [devices, setDevices] = useState<BranDevice[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [visibleCount, setVisibleCount] = useState(0);
  const revealTimers = useRef<number[]>([]);
  const location = useLocation();
  const navigate = useNavigate();

  const clearTimers = () => {
    revealTimers.current.forEach((t) => clearTimeout(t));
    revealTimers.current = [];
  };

  const runScan = useCallback(async () => {
    setPhase("scanning");
    setVisibleCount(0);
    setDevices([]);
    clearTimers();
    try {
      const st = await api.bran.status();
      setStatus(st);
      if (!st.connected) {
        setPhase("error");
        return;
      }
      // Scan: discovers devices AND auto-imports to Odoo
      const devs = await api.bran.scan();
      if (devs.length === 0) {
        setDevices([]);
        setPhase("empty");
        return;
      }
      setDevices(devs);
      setPhase("revealing");
      devs.forEach((_, i) => {
        const timer = window.setTimeout(() => {
          setVisibleCount((n) => n + 1);
          if (i === devs.length - 1) {
            setPhase("done");
          }
        }, 600 + i * 400);
        revealTimers.current.push(timer);
      });
    } catch (err) {
      console.error("[Bran] scan error:", err);
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    if (location.pathname !== "/bran") clearTimers();
    return clearTimers;
  }, [location.pathname]);

  // Live refresh every 5s when scan is complete
  useEffect(() => {
    if (location.pathname !== "/bran" || phase !== "done") return;
    const interval = setInterval(async () => {
      try {
        const devs = await api.bran.devices();
        setDevices(devs);
        setVisibleCount(devs.length);
      } catch {
        // silent
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [location.pathname, phase]);

  const RadarIcon = ({ className = "w-12 h-12" }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
      <circle cx="12" cy="12" r="6.5" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" />
      <line x1="12" y1="12" x2="18" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );

  if (phase === "idle") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#faf8f5] gap-6">
        <button
          onClick={runScan}
          className="group relative w-36 h-36 rounded-full bg-white shadow-lg border border-[#f0ece7] flex items-center justify-center hover:shadow-xl hover:border-[#f0ded8] transition-all active:scale-95"
        >
          <RadarIcon className="w-16 h-16 text-[#c45d3e] group-hover:scale-110 transition-transform" />
        </button>
        <div className="text-center">
          <p className="text-[#c45d3e] font-semibold text-base">Scanner le réseau</p>
          <p className="text-[#8a837b] text-sm mt-1">Détecter et importer les appareils connectés</p>
        </div>
      </div>
    );
  }

  if (phase === "scanning") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#faf8f5] gap-6">
        <div className="relative w-36 h-36">
          <div className="absolute inset-0 rounded-full border-2 border-[#d4915e]/30 animate-ping opacity-30" />
          <div className="absolute inset-4 rounded-full border-2 border-[#c45d3e]/40 animate-ping opacity-40 [animation-delay:300ms]" />
          <div className="absolute inset-8 rounded-full border-2 border-[#a84e34]/50 animate-ping opacity-50 [animation-delay:600ms]" />
          <div className="absolute inset-0 flex items-center justify-center">
            <RadarIcon className="w-14 h-14 text-[#c45d3e] animate-[spin_3s_linear_infinite]" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-[#c45d3e] font-semibold text-base">Bran scanne le réseau...</p>
          <p className="text-[#8a837b] text-sm mt-1">Détection et import automatique</p>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#faf8f5] px-8 text-center">
        <div className="w-16 h-16 rounded-full bg-[#faf0ef] flex items-center justify-center mb-4">
          <RadarIcon className="w-8 h-8 text-[#c45d5d]" />
        </div>
        <p className="text-[#5a524b] font-semibold text-base">Bran est hors ligne</p>
        <p className="text-[#8a837b] text-sm mt-1">
          Impossible de se connecter à Jeedom.
          {status?.jeedom_url && (
            <span className="block text-xs mt-1 text-[#d4cdc5]">{status.jeedom_url}</span>
          )}
        </p>
        <button
          onClick={runScan}
          className="mt-6 px-6 py-2.5 bg-[#c45d3e] text-white rounded-xl text-sm font-medium hover:bg-[#a84e34] transition-colors"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (phase === "empty") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#faf8f5] px-8 text-center">
        <div className="w-16 h-16 rounded-full bg-[#f0ece7] flex items-center justify-center mb-4">
          <RadarIcon className="w-8 h-8 text-[#d4cdc5]" />
        </div>
        <p className="text-[#5a524b] font-semibold text-base">Aucun appareil détecté</p>
        <p className="text-[#8a837b] text-sm mt-1">
          Jeedom est connecté mais aucun équipement n'a été trouvé.
        </p>
        <button
          onClick={runScan}
          className="mt-6 px-6 py-2.5 bg-[#c45d3e] text-white rounded-xl text-sm font-medium hover:bg-[#a84e34] transition-colors"
        >
          Rescanner
        </button>
      </div>
    );
  }

  const newCount = devices.filter((d) => d.is_new).length;
  const isRevealing = phase === "revealing";

  return (
    <div className="h-full overflow-y-auto bg-[#faf8f5]">
      <div className="px-4 pt-5 pb-4 space-y-4">
        {/* Status bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isRevealing ? (
              <span className="w-2 h-2 rounded-full bg-[#d4915e] animate-pulse" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-[#7a9e7e]" />
            )}
            <span className="text-xs text-[#8a8078]">
              {isRevealing
                ? `${visibleCount}/${devices.length} détecté${visibleCount > 1 ? "s" : ""}...`
                : `${devices.length} appareil${devices.length > 1 ? "s" : ""} dans Maison`}
            </span>
          </div>
          {phase === "done" && newCount > 0 && (
            <span className="text-xs text-[#c45d3e] font-medium">
              {newCount} nouveau{newCount > 1 ? "x" : ""}
            </span>
          )}
        </div>

        {/* Device cards */}
        {devices.slice(0, visibleCount).map((device, index) => {
          const infoCmds = device.commands.filter((c) => c.type === "info" && c.value != null);

          return (
            <div
              key={device.id}
              onClick={() => {
                if (device.linked_equipment_id) {
                  navigate(`/scan/${device.linked_equipment_id}`);
                }
              }}
              className={`bg-white rounded-2xl p-4 shadow-sm border transition-all duration-500 cursor-pointer hover:shadow-md ${
                device.is_new ? "border-[#f0ded8]" : "border-[#e8f0e9]"
              } ${index < visibleCount ? "animate-[fadeSlideIn_0.4s_ease-out_forwards]" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-[#3d3833] font-medium text-sm truncate">{device.name}</p>
                    {device.is_new ? (
                      <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-[#fdf6ef] text-[#d4915e] shrink-0">
                        nouveau
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-[#e8f0e9] text-[#5a8a60] shrink-0">
                        lié
                      </span>
                    )}
                  </div>
                  {device.object_name && (
                    <p className="text-[#8a837b] text-xs mt-0.5">{device.object_name}</p>
                  )}
                  {device.linked_equipment_name && (
                    <p className="text-[#5a8a60] text-xs mt-0.5">
                      → {device.linked_equipment_name}
                    </p>
                  )}
                </div>
                {/* Chevron to detail */}
                <div className="shrink-0 text-[#d4cdc5] mt-1">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z" />
                  </svg>
                </div>
              </div>

              {/* Live sensor values */}
              {infoCmds.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-3">
                  {infoCmds.map((cmd) => (
                    <div
                      key={cmd.id}
                      className="flex items-baseline gap-1 bg-[#faf8f5] rounded-lg px-2.5 py-1.5"
                    >
                      <span className="text-[#3d3833] font-semibold text-sm">{cmd.value}</span>
                      {cmd.unite && (
                        <span className="text-[#8a837b] text-xs">{cmd.unite}</span>
                      )}
                      <span className="text-[#8a837b] text-[10px] ml-1">{cmd.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {isRevealing && (
          <div className="flex items-center justify-center gap-2 py-3">
            <RadarIcon className="w-5 h-5 text-[#d4915e] animate-[spin_3s_linear_infinite]" />
            <span className="text-xs text-[#d4915e]">Scan en cours...</span>
          </div>
        )}

        {phase === "done" && (
          <button
            onClick={runScan}
            className="w-full flex items-center justify-center gap-2 py-3 text-sm text-[#8a837b] hover:text-[#c45d3e] transition-colors"
          >
            <RadarIcon className="w-4 h-4" />
            Rescanner
          </button>
        )}
      </div>
    </div>
  );
}
