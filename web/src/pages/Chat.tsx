import { useEffect, useRef, useState } from "react";
import { api, type Appliance, type ChatMessage } from "../api";
import { useAppContext } from "../AppContext";
import MessageBubble from "../components/MessageBubble";
import LoadingDots from "../components/LoadingDots";
import MicButton from "../components/MicButton";

interface DisplayMessage extends ChatMessage {
  imageUrl?: string;
  audioUrl?: string;
  toolsUsed?: string[];
}

const HODOR_IMAGE_URL =
  "https://funko.com/dw/image/v2/BGTS_PRD/on/demandware.static/-/Sites-funko-master-catalog/default/dw99acc27a/images/funko/45053-1.png?sh=800&sw=800";

const WELCOME_MESSAGES: DisplayMessage[] = [
  { role: "assistant", content: "Salut ! Moi c'est Hodoor" },
  { role: "assistant", content: "Je gère l'entretien de ta maison. Commence par me montrer tes appareils." },
  { role: "assistant", content: "Prends en photo l'étiquette technique (marque, modèle, serial). Pas d'étiquette ? L'appareil seul suffit, je me débrouille." },
];

export default function Chat({ visible = true }: { visible?: boolean }) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [showHodor, setShowHodor] = useState(false);
  const [welcomeShown, setWelcomeShown] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const speechBaseRef = useRef("");
  const hodorTimeoutRef = useRef<number | null>(null);
  const { pendingChatMessage, setPendingChatMessage } = useAppContext();

  useEffect(() => {
    api.chat
      .history()
      .then((history) => {
        setMessages(history);
        if (history.length > 0) setWelcomeShown(WELCOME_MESSAGES.length);
      })
      .catch(() => {})
      .finally(() => setInitialLoad(false));
    api.appliances.list().then(setAppliances).catch(() => {});
  }, []);

  // Stagger welcome messages when no history
  // Delays based on reading time of the previous message
  const welcomeDelays = [500, 1500, 2500];
  useEffect(() => {
    if (initialLoad || messages.length > 0 || welcomeShown >= WELCOME_MESSAGES.length) return;
    const timer = setTimeout(() => {
      setWelcomeShown((n) => n + 1);
    }, welcomeDelays[welcomeShown]);
    return () => clearTimeout(timer);
  }, [initialLoad, messages.length, welcomeShown]);

  const [inflightTools, setInflightTools] = useState<string[]>([]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, inflightTools]);

  // Poll in-flight tool calls during loading
  useEffect(() => {
    if (!loading) { setInflightTools([]); return; }
    const poll = setInterval(() => {
      api.chat.toolsInflight().then((r) => setInflightTools(r.tools)).catch(() => {});
    }, 1500);
    return () => clearInterval(poll);
  }, [loading]);

  useEffect(() => {
    return () => {
      if (hodorTimeoutRef.current !== null) {
        window.clearTimeout(hodorTimeoutRef.current);
      }
    };
  }, []);

  const triggerHodor = () => {
    setShowHodor(true);
    if (hodorTimeoutRef.current !== null) {
      window.clearTimeout(hodorTimeoutRef.current);
    }
    hodorTimeoutRef.current = window.setTimeout(() => {
      setShowHodor(false);
      hodorTimeoutRef.current = null;
    }, 2200);
  };

  // Prepend welcome messages when first real message is sent
  const ensureWelcomeInHistory = () => {
    if (messages.length === 0 && welcomeShown > 0) {
      return [...WELCOME_MESSAGES.slice(0, welcomeShown)];
    }
    return [];
  };

  const sendText = async (text: string) => {
    if (text.trim().toLowerCase() === "hold the door") {
      triggerHodor();
    }
    const isSlashReload = text.trim().toLowerCase().startsWith("/scan") || text.trim().toLowerCase().startsWith("/reset");
    const welcome = ensureWelcomeInHistory();
    const userMsg: DisplayMessage = { role: "user", content: text };
    setMessages((prev) => [...welcome, ...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat.send(text);
      if (isSlashReload) {
        window.location.reload();
        return;
      }
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, audioUrl: res.audio_url ?? undefined, toolsUsed: res.tools_used }]);
      api.appliances.list().then(setAppliances).catch(() => {});
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : "Erreur.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Erreur: ${detail}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Auto-send pending message from Scan page "Generate plan" button
  useEffect(() => {
    if (visible && pendingChatMessage && !loading && !initialLoad) {
      sendText(pendingChatMessage);
      setPendingChatMessage(null);
    }
  }, [visible, pendingChatMessage, loading, initialLoad]);

  const sendPhoto = async (file: File) => {
    const imageUrl = URL.createObjectURL(file);
    const caption = input.trim();
    const welcome = ensureWelcomeInHistory();
    const userMsg: DisplayMessage = {
      role: "user",
      content: caption,
      imageUrl,
    };
    setMessages((prev) => [...welcome, ...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat.sendPhoto(caption || "Analyse cette photo.", file);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, audioUrl: res.audio_url ?? undefined, toolsUsed: res.tools_used }]);
      api.appliances.list().then(setAppliances).catch(() => {});
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : "Erreur.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Erreur: ${detail}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const submit = () => {
    const text = input.trim();
    if (!text || loading) return;
    sendText(text);
  };

  return (
    <div className="flex flex-col h-full bg-[#faf8f5] relative">
      {showHodor && (
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <img
            src={HODOR_IMAGE_URL}
            alt="Hodor holding the door"
            className="w-[78vw] max-w-[420px] hodor-pop"
          />
        </div>
      )}

      {/* Messages */}
      <div className={`flex-1 overflow-y-auto px-4 py-4 space-y-1 ${appliances.length >= 3 && !loading ? "pb-20" : ""}`}>
        {initialLoad ? (
          <div className="flex justify-center py-8">
            <span className="text-gray-400 text-sm">Chargement...</span>
          </div>
        ) : messages.length === 0 ? (
          <>
            {WELCOME_MESSAGES.slice(0, welcomeShown).map((m, i) => (
              <MessageBubble key={`welcome-${i}`} role={m.role} content={m.content} />
            ))}
            {welcomeShown < WELCOME_MESSAGES.length && <LoadingDots />}
          </>
        ) : (
          messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} imageUrl={m.imageUrl} audioUrl={m.audioUrl} toolsUsed={m.toolsUsed} />
          ))
        )}
        {loading && (
          <div>
            <LoadingDots />
            {inflightTools.length > 0 && (
              <div className="flex flex-wrap gap-1 ml-1 -mt-1 mb-2">
                {inflightTools.map((t, i) => (
                  <span key={i} className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-[#f0ece7] text-[#8a837b] animate-pulse">
                    {t.replace("search_records", "Recherche Odoo").replace("create_record", "Création Odoo").replace("update_record", "MAJ Odoo").replace("get_record", "Lecture Odoo").replace("search_product_docs", "Docs produit").replace("search_common_issues", "Pannes connues").replace("set_mode", "Mode")}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Generate plan button */}
      {appliances.length >= 3 && !loading && (
        <div className="px-3 pb-2 shrink-0">
          <button
            onClick={() => sendText("J'ai fini, fais le récap et le plan de prévention")}
            className="w-full bg-[#c45d3e] text-white rounded-xl py-3 font-semibold text-sm shadow-sm flex items-center justify-center gap-2 hover:bg-[#a84e34] transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
            </svg>
            Générer mon plan d'entretien
          </button>
        </div>
      )}

      {/* Input bar */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) { sendPhoto(file); e.target.value = ""; }
        }}
      />
      <div className="px-4 py-3 shrink-0">
        <div className="flex items-center gap-2 bg-white rounded-full px-4 py-1.5 shadow-sm border border-[#f0ece7]">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } }}
            placeholder="Demander à Hodoor..."
            disabled={loading}
            className="flex-1 min-w-0 py-2 text-[#3d3833] placeholder-gray-400 text-sm bg-transparent focus:outline-none"
          />

          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={loading}
            className="p-1.5 text-gray-400 hover:text-[#c45d3e] disabled:opacity-40 transition-colors shrink-0"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4z" />
              <path d="M9 3L7.17 5H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2h-3.17L15 3H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" />
            </svg>
          </button>

          <MicButton
            visible={visible}
            onListeningChange={(isListening) => {
              if (isListening) {
                speechBaseRef.current = input.trim();
              } else {
                speechBaseRef.current = "";
              }
            }}
            onTranscript={(text) => {
              const prefix = speechBaseRef.current ? `${speechBaseRef.current} ` : "";
              setInput(`${prefix}${text}`.trim());
            }}
            disabled={loading}
          />

          <button
            type="button"
            onClick={submit}
            disabled={!input.trim() || loading}
            className="w-9 h-9 bg-[#c45d3e] rounded-full flex items-center justify-center disabled:opacity-40 shrink-0 hover:bg-[#a84e34] transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="white" className="w-4 h-4">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
