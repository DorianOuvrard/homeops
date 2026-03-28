import { useEffect, useRef, useState } from "react";
import { api, type Appliance, type ChatMessage } from "../api";
import ApplianceCard from "../components/ApplianceCard";
import MessageBubble from "../components/MessageBubble";
import LoadingDots from "../components/LoadingDots";

export default function Scan() {
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [loadingAppliances, setLoadingAppliances] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingChat, setLoadingChat] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [tipOpen, setTipOpen] = useState(
    () => localStorage.getItem("scan_tip_dismissed") !== "true",
  );
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const refreshAppliances = () => {
    api.appliances
      .list()
      .then(setAppliances)
      .catch(() => setError("Impossible de charger les appareils."))
      .finally(() => setLoadingAppliances(false));
  };

  useEffect(() => {
    refreshAppliances();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loadingChat]);

  const sendScanPhoto = async (file: File) => {
    const userMsg: ChatMessage = {
      role: "user",
      content: "[photo] Identifie cet appareil.",
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoadingChat(true);
    try {
      const res = await api.chat.sendPhoto("Identifie et enregistre cet appareil.", file);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      refreshAppliances();
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : "Erreur.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Erreur: ${detail}` },
      ]);
    } finally {
      setLoadingChat(false);
    }
  };

  const sendText = async (text: string) => {
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoadingChat(true);
    try {
      const res = await api.chat.send(text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      refreshAppliances();
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : "Erreur.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Erreur: ${detail}` },
      ]);
    } finally {
      setLoadingChat(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      sendScanPhoto(file);
      e.target.value = "";
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 relative">
      <div className="flex-1 overflow-y-auto">
        {/* Camera viewfinder zone */}
        <div className="relative">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={loadingChat}
            className="w-full bg-gray-800 aspect-4/3 flex flex-col items-center justify-center disabled:opacity-50 transition-colors relative overflow-hidden"
          >
            {/* Viewfinder blue brackets */}
            <div className="absolute inset-8 sm:inset-12">
              <div className="absolute top-0 left-0 w-8 h-8 border-t-3 border-l-3 border-[#1a237e] rounded-tl" />
              <div className="absolute top-0 right-0 w-8 h-8 border-t-3 border-r-3 border-[#1a237e] rounded-tr" />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b-3 border-l-3 border-[#1a237e] rounded-bl" />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-3 border-r-3 border-[#1a237e] rounded-br" />
            </div>

            {/* Placeholder camera icon when no photo */}
            <svg viewBox="0 0 24 24" fill="white" className="w-12 h-12 opacity-20">
              <path d="M9 3L7.17 5H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2h-3.17L15 3H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" />
              <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4z" />
            </svg>
          </button>

          {/* Bottom overlay text */}
          <div className="absolute bottom-8 left-0 right-0 px-4">
            <p className="text-white text-sm text-center font-medium bg-black/50 rounded-xl mx-auto max-w-xs px-4 py-2.5">
              {loadingChat
                ? "Identification en cours..."
                : "Alignez la plaque signalétique dans le cadre"}
            </p>
          </div>
        </div>

        {/* Identification badge card */}
        <div className="px-4 -mt-5 relative z-10">
          <div className="bg-white rounded-2xl shadow-md px-5 py-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-[#1a237e] rounded-xl flex items-center justify-center shrink-0">
              <svg viewBox="0 0 24 24" fill="white" className="w-6 h-6">
                <path d="M3 11h8V3H3v8zm2-6h4v4H5V5zm8-2v8h8V3h-8zm6 6h-4V5h4v4zM3 21h8v-8H3v8zm2-6h4v4H5v-4zm13-2h-2v3h-3v2h3v3h2v-3h3v-2h-3v-3z" />
              </svg>
            </div>
            <div>
              <p className="font-bold text-gray-900">Identification d&apos;Hodoor</p>
              <p className="text-xs text-gray-400 font-semibold tracking-wide uppercase">
                {loadingChat ? (
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-[#f57c00] rounded-full animate-pulse" />
                    Analyse en cours...
                  </span>
                ) : (
                  "Analyse en temps réel"
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Chat messages from scan */}
        {messages.length > 0 && (
          <div className="px-4 pt-4 pb-2 space-y-1">
            {messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} content={m.content} />
            ))}
            {loadingChat && <LoadingDots />}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Follow-up text input */}
        {messages.length > 0 && (
          <div className="px-4 pb-3">
            <div className="flex items-center gap-2 bg-white rounded-full px-4 py-1.5 shadow-sm border border-gray-100">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    const text = input.trim();
                    if (text && !loadingChat) sendText(text);
                  }
                }}
                placeholder="Suite de la conversation..."
                disabled={loadingChat}
                className="flex-1 min-w-0 py-2 text-gray-900 placeholder-gray-400 text-sm bg-transparent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => {
                  const text = input.trim();
                  if (text && !loadingChat) sendText(text);
                }}
                disabled={!input.trim() || loadingChat}
                className="w-9 h-9 bg-[#1a237e] rounded-full flex items-center justify-center disabled:opacity-30 shrink-0 hover:bg-[#283593] transition-colors"
              >
                <svg viewBox="0 0 24 24" fill="white" className="w-4 h-4">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Appliance list */}
        <div className="px-4 pt-5 pb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-gray-900 font-bold text-sm uppercase tracking-wide">
              Historique récent
            </h2>
            {appliances.length > 0 && (
              <span className="text-[#1a237e] text-sm font-semibold">Tout voir</span>
            )}
          </div>
          {error && (
            <p className="text-red-500 text-sm mb-3">{error}</p>
          )}
          {loadingAppliances ? (
            <p className="text-gray-400 text-sm">Chargement...</p>
          ) : appliances.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-400 text-sm">Aucun appareil enregistré.</p>
              <p className="text-gray-400 text-xs mt-1">Scannez votre premier appareil ci-dessus.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {appliances.map((a) => (
                <ApplianceCard key={a.id} appliance={a} />
              ))}
            </div>
          )}
        </div>

      </div>

      {/* Floating Pro tip */}
      {tipOpen && (
        <div className="absolute bottom-2 left-3 right-3 z-20">
          <div className="bg-[#fff3e0] rounded-xl p-3.5 border-l-4 border-[#f57c00] shadow-lg flex gap-3 items-start">
            <div className="shrink-0 mt-0.5">
              <svg viewBox="0 0 24 24" fill="#f57c00" className="w-5 h-5">
                <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[#f57c00] font-bold text-xs uppercase tracking-wide mb-1">
                Conseil Pro
              </p>
              <p className="text-gray-600 text-sm leading-relaxed">
                Assurez-vous qu&apos;il y a assez de lumière pour une lecture optimale des petits caractères.
              </p>
            </div>
            <button
              onClick={() => {
                setTipOpen(false);
                localStorage.setItem("scan_tip_dismissed", "true");
              }}
              className="shrink-0 p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
