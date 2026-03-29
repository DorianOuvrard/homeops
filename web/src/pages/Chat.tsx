import { useEffect, useRef, useState } from "react";
import { api, type ChatMessage } from "../api";
import MessageBubble from "../components/MessageBubble";
import LoadingDots from "../components/LoadingDots";
import MicButton from "../components/MicButton";

interface DisplayMessage extends ChatMessage {
  imageUrl?: string;
  audioUrl?: string;
}

const HODOR_IMAGE_URL =
  "https://funko.com/dw/image/v2/BGTS_PRD/on/demandware.static/-/Sites-funko-master-catalog/default/dw99acc27a/images/funko/45053-1.png?sh=800&sw=800";

export default function Chat() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [showHodor, setShowHodor] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const speechBaseRef = useRef("");
  const hodorTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    api.chat
      .history()
      .then(setMessages)
      .catch(() => {})
      .finally(() => setInitialLoad(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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

  const sendText = async (text: string) => {
    if (text.trim().toLowerCase() === "hold the door") {
      triggerHodor();
    }
    const userMsg: DisplayMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat.send(text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, audioUrl: res.audio_url ?? undefined }]);
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

  const sendPhoto = async (file: File) => {
    const imageUrl = URL.createObjectURL(file);
    const caption = input || "Analyse cette photo.";
    const userMsg: DisplayMessage = {
      role: "user",
      content: caption,
      imageUrl,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat.sendPhoto(caption, file);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, audioUrl: res.audio_url ?? undefined }]);
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
    <div className="flex flex-col h-full bg-gray-50">
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
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {initialLoad ? (
          <div className="flex justify-center py-8">
            <span className="text-gray-400 text-sm">Chargement...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            {/* Pulsing voice circle with glow */}
            <div className="relative w-44 h-44 mb-8 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full bg-[#c5cae9]/30 voice-pulse-outer" />
              <div className="absolute inset-4 rounded-full bg-[#9fa8da]/30 voice-pulse" />
              <div className="absolute inset-8 rounded-full bg-[#7986cb]/20" />
              <div className="relative w-24 h-24 rounded-full bg-linear-to-br from-[#1a237e] to-[#283593] flex items-center justify-center shadow-xl">
                {/* Sound wave bars */}
                <div className="flex items-center gap-0.75">
                  <span className="w-0.75 h-4 bg-white rounded-full animate-pulse" style={{ animationDelay: "0ms" }} />
                  <span className="w-0.75 h-6 bg-white rounded-full animate-pulse" style={{ animationDelay: "150ms" }} />
                  <span className="w-0.75 h-8 bg-white rounded-full animate-pulse" style={{ animationDelay: "300ms" }} />
                  <span className="w-0.75 h-6 bg-white rounded-full animate-pulse" style={{ animationDelay: "150ms" }} />
                  <span className="w-0.75 h-4 bg-white rounded-full animate-pulse" style={{ animationDelay: "0ms" }} />
                </div>
              </div>
            </div>
            <p className="text-[#f57c00] font-semibold text-xs tracking-[0.25em] uppercase mb-3">
              En écoute
            </p>
            <p className="text-gray-800 font-bold text-xl">
              Comment puis-je
            </p>
            <p className="text-gray-800 font-bold text-xl">
              vous aider ?
            </p>
          </div>
        ) : (
          messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} imageUrl={m.imageUrl} audioUrl={m.audioUrl} />
          ))
        )}
        {loading && <LoadingDots />}
        <div ref={bottomRef} />
      </div>

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
        <div className="flex items-center gap-2 bg-white rounded-full px-4 py-1.5 shadow-sm border border-gray-100">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } }}
            placeholder="Demander à Hodoor..."
            disabled={loading}
            className="flex-1 min-w-0 py-2 text-gray-900 placeholder-gray-400 text-sm bg-transparent focus:outline-none"
          />

          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={loading}
            className="p-1.5 text-gray-400 hover:text-[#1a237e] disabled:opacity-40 transition-colors shrink-0"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4z" />
              <path d="M9 3L7.17 5H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2h-3.17L15 3H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" />
            </svg>
          </button>

          <MicButton
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
            className="w-9 h-9 bg-[#1a237e] rounded-full flex items-center justify-center disabled:opacity-30 shrink-0 hover:bg-[#283593] transition-colors"
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
