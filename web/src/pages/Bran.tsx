import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, type BranDevice, type BranStatus, type Appliance } from "../api";

type LinkingState = { deviceId: number } | null;
type Phase = "idle" | "scanning" | "revealing" | "done" | "error" | "empty";

export default function Bran() {
  const [status, setStatus] = useState<BranStatus | null>(null);
  const [devices, setDevices] = useState<BranDevice[]>([]);
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [visibleCount, setVisibleCount] = useState(0);
  const [linking, setLinking] = useState<LinkingState>(null);
  const revealTimers = useRef<number[]>([]);
  const location = useLocation();

  const clearTimers = () => {
    revealTimers.current.forEach((t) => clearTimeout(t));
    revealTimers.current = [];
  };

  const fetchData = useCallback(async () => {
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
      const [devs, apps] = await Promise.all([
        api.bran.devices(),
        api.appliances.list(),
      ]);
      setAppliances(apps);
      if (devs.length === 0) {
        setDevices([]);
        setPhase("empty");
        return;
      }
      setDevices(devs);
      // Progressive reveal: show devices one by one
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
      console.error("[Bran] fetch error:", err);
      setPhase("error");
    }
  }, []);

  // Reset to idle when navigating away, don't auto-scan
  useEffect(() => {
    if (location.pathname !== "/bran") {
      clearTimers();
    }
    return clearTimers;
  }, [location.pathname]);

  // Auto-refresh values every 5s when scan is done
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

  const handleLink = async (deviceId: number, equipmentId: number) => {
    try {
      await api.bran.link(deviceId, equipmentId);
      setDevices((prev) =>
        prev.map((d) =>
          d.id === deviceId
            ? {
                ...d,
                linked_equipment_id: equipmentId,
                linked_equipment_name:
                  appliances.find((a) => a.id === equipmentId)?.name,
              }
            : d,
        ),
      );
    } catch (err) {
      console.error("[Bran] link error:", err);
    }
    setLinking(null);
  };

  const handleImport = async (deviceId: number) => {
    try {
      const result = await api.bran.import(deviceId);
      setDevices((prev) =>
        prev.map((d) =>
          d.id === deviceId
            ? {
                ...d,
                linked_equipment_id: result.equipment_id,
                linked_equipment_name: result.equipment_name,
              }
            : d,
        ),
      );
    } catch (err) {
      console.error("[Bran] import error:", err);
    }
  };

  const handleUnlink = async (deviceId: number) => {
    try {
      await api.bran.unlink(deviceId);
      setDevices((prev) =>
        prev.map((d) =>
          d.id === deviceId
            ? { ...d, linked_equipment_id: undefined, linked_equipment_name: undefined }
            : d,
        ),
      );
    } catch (err) {
      console.error("[Bran] unlink error:", err);
    }
  };

  const RadarIcon = ({ className = "w-12 h-12" }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
      <circle cx="12" cy="12" r="6.5" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" />
      <line x1="12" y1="12" x2="18" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );

  // Idle: show scan button
  if (phase === "idle") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 gap-6">
        <button
          onClick={fetchData}
          className="group relative w-36 h-36 rounded-full bg-white shadow-lg border border-gray-100 flex items-center justify-center hover:shadow-xl hover:border-indigo-200 transition-all active:scale-95"
        >
          <RadarIcon className="w-16 h-16 text-[#1a237e] group-hover:scale-110 transition-transform" />
        </button>
        <div className="text-center">
          <p className="text-[#1a237e] font-semibold text-base">Scanner le réseau</p>
          <p className="text-gray-400 text-sm mt-1">Détecter les appareils connectés</p>
        </div>
      </div>
    );
  }

  // Scanning animation
  if (phase === "scanning") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 gap-6">
        <div className="relative w-36 h-36">
          <div className="absolute inset-0 rounded-full border-2 border-indigo-200 animate-ping opacity-30" />
          <div className="absolute inset-4 rounded-full border-2 border-indigo-300 animate-ping opacity-40 [animation-delay:300ms]" />
          <div className="absolute inset-8 rounded-full border-2 border-indigo-400 animate-ping opacity-50 [animation-delay:600ms]" />
          <div className="absolute inset-0 flex items-center justify-center">
            <RadarIcon className="w-14 h-14 text-[#1a237e] animate-[spin_3s_linear_infinite]" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-[#1a237e] font-semibold text-base">Bran scanne le réseau...</p>
          <p className="text-gray-400 text-sm mt-1">Recherche d'appareils connectés</p>
        </div>
      </div>
    );
  }

  // Not connected
  if (phase === "error") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 px-8 text-center">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-4">
          <RadarIcon className="w-8 h-8 text-red-400" />
        </div>
        <p className="text-gray-700 font-semibold text-base">Bran est hors ligne</p>
        <p className="text-gray-400 text-sm mt-1">
          Impossible de se connecter à Jeedom.
          {status?.jeedom_url && (
            <span className="block text-xs mt-1 text-gray-300">{status.jeedom_url}</span>
          )}
        </p>
        <button
          onClick={fetchData}
          className="mt-6 px-6 py-2.5 bg-[#1a237e] text-white rounded-xl text-sm font-medium hover:bg-[#283593] transition-colors"
        >
          Réessayer
        </button>
      </div>
    );
  }

  // No devices found
  if (phase === "empty") {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 px-8 text-center">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <RadarIcon className="w-8 h-8 text-gray-300" />
        </div>
        <p className="text-gray-700 font-semibold text-base">Aucun appareil détecté</p>
        <p className="text-gray-400 text-sm mt-1">
          Jeedom est connecté mais aucun équipement n'a été trouvé.
        </p>
        <button
          onClick={fetchData}
          className="mt-6 px-6 py-2.5 bg-[#1a237e] text-white rounded-xl text-sm font-medium hover:bg-[#283593] transition-colors"
        >
          Rescanner
        </button>
      </div>
    );
  }

  const linkedCount = devices.filter((d) => d.linked_equipment_id).length;
  const isRevealing = phase === "revealing";

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="px-4 pt-5 pb-4 space-y-4">
        {/* Status bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isRevealing ? (
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-green-400" />
            )}
            <span className="text-xs text-gray-500">
              {isRevealing
                ? `${visibleCount}/${devices.length} détecté${visibleCount > 1 ? "s" : ""}...`
                : `${devices.length} appareil${devices.length > 1 ? "s" : ""} détecté${devices.length > 1 ? "s" : ""}`}
            </span>
          </div>
          {phase === "done" && (
            <span className="text-xs text-gray-400">
              {linkedCount}/{devices.length} associé{linkedCount > 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Device cards */}
        {devices.slice(0, visibleCount).map((device, index) => {
          const infoCmds = device.commands.filter((c) => c.type === "info" && c.value != null);
          const isLinked = !!device.linked_equipment_id;
          const isLinking = linking?.deviceId === device.id;

          return (
            <div
              key={device.id}
              className={`bg-white rounded-xl p-4 shadow-sm border transition-all duration-500 ${
                isLinked ? "border-green-100" : "border-gray-100"
              } ${index < visibleCount ? "animate-[fadeSlideIn_0.4s_ease-out_forwards]" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-gray-900 font-medium text-sm truncate">{device.name}</p>
                    {isLinked && (
                      <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-green-50 text-green-600 shrink-0">
                        lié
                      </span>
                    )}
                  </div>
                  {device.object_name && (
                    <p className="text-gray-400 text-xs mt-0.5">{device.object_name}</p>
                  )}
                  {isLinked && device.linked_equipment_name && (
                    <p className="text-green-600 text-xs mt-0.5">
                      → {device.linked_equipment_name}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="shrink-0 flex items-center gap-1">
                  {isLinked ? (
                    <button
                      onClick={() => handleUnlink(device.id)}
                      className="w-8 h-8 rounded-full flex items-center justify-center text-green-400 hover:text-red-400 hover:bg-red-50 transition-colors"
                      title="Dissocier"
                    >
                      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                        <path d="M17 7h-4v2h4c1.65 0 3 1.35 3 3s-1.35 3-3 3h-4v2h4c2.76 0 5-2.24 5-5s-2.24-5-5-5zm-6 8H7c-1.65 0-3-1.35-3-3s1.35-3 3-3h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-2zm-3-4h8v2H8z" />
                      </svg>
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => handleImport(device.id)}
                        className="px-3 py-1.5 rounded-lg bg-[#1a237e] text-white text-xs font-medium hover:bg-[#283593] transition-colors"
                        title="Créer dans Maison"
                      >
                        + Maison
                      </button>
                      <button
                        onClick={() => setLinking({ deviceId: device.id })}
                        className="w-8 h-8 rounded-full flex items-center justify-center text-gray-300 hover:text-[#1a237e] hover:bg-indigo-50 transition-colors"
                        title="Associer à un équipement existant"
                      >
                        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                          <path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z" />
                        </svg>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Live sensor values */}
              {infoCmds.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-3">
                  {infoCmds.map((cmd) => (
                    <div
                      key={cmd.id}
                      className="flex items-baseline gap-1 bg-gray-50 rounded-lg px-2.5 py-1.5"
                    >
                      <span className="text-gray-900 font-semibold text-sm">{cmd.value}</span>
                      {cmd.unite && (
                        <span className="text-gray-400 text-xs">{cmd.unite}</span>
                      )}
                      <span className="text-gray-400 text-[10px] ml-1">{cmd.name}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Linking dropdown */}
              {isLinking && (
                <div className="mt-3 border-t border-gray-100 pt-3">
                  <p className="text-xs text-gray-500 mb-2">Associer à un équipement Odoo :</p>
                  <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto">
                    {appliances.map((app) => (
                      <button
                        key={app.id}
                        onClick={() => handleLink(device.id, app.id)}
                        className="text-left px-3 py-2 rounded-lg text-sm hover:bg-indigo-50 hover:text-[#1a237e] transition-colors"
                      >
                        <span className="font-medium">{app.name}</span>
                        {app.category && (
                          <span className="text-gray-400 text-xs ml-2">{app.category}</span>
                        )}
                      </button>
                    ))}
                    <button
                      onClick={() => setLinking(null)}
                      className="text-center px-3 py-1.5 text-xs text-gray-400 hover:text-gray-600"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Scanning indicator during reveal */}
        {isRevealing && (
          <div className="flex items-center justify-center gap-2 py-3">
            <RadarIcon className="w-5 h-5 text-indigo-400 animate-[spin_3s_linear_infinite]" />
            <span className="text-xs text-indigo-400">Scan en cours...</span>
          </div>
        )}

        {/* Rescan button */}
        {phase === "done" && (
          <button
            onClick={fetchData}
            className="w-full flex items-center justify-center gap-2 py-3 text-sm text-gray-400 hover:text-[#1a237e] transition-colors"
          >
            <RadarIcon className="w-4 h-4" />
            Rescanner
          </button>
        )}
      </div>
    </div>
  );
}
