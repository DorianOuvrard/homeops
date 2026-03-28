import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Appliance, type ChatMessage } from "../api";
import MessageBubble from "../components/MessageBubble";
import LoadingDots from "../components/LoadingDots";

function BackIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
      <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" />
    </svg>
  );
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export default function ApplianceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const equipmentId = parseInt(id ?? "0", 10);

  const [appliance, setAppliance] = useState<Appliance | null>(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.appliances
      .get(equipmentId)
      .then(setAppliance)
      .catch(() => navigate("/scan"))
      .finally(() => setLoading(false));

    api.appliances
      .chatHistory(equipmentId)
      .then(setMessages)
      .catch(() => {});
  }, [equipmentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  const sendMessage = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setChatLoading(true);
    try {
      const res = await api.appliances.chat(equipmentId, text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : "Erreur.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Erreur: ${detail}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <span className="text-gray-400">Chargement...</span>
      </div>
    );
  }

  const upcoming = appliance?.maintenance_requests?.filter(
    (r) => r.schedule_date && new Date(r.schedule_date) >= new Date()
  ) ?? [];
  const past = appliance?.maintenance_requests?.filter(
    (r) => !r.schedule_date || new Date(r.schedule_date) < new Date()
  ) ?? [];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-[#1a237e] px-4 py-3 flex items-center gap-3 flex-shrink-0">
        <button onClick={() => navigate("/scan")} className="text-white/70 hover:text-white">
          <BackIcon />
        </button>
        <div>
          <h1 className="text-white font-bold text-base leading-tight">
            {appliance?.name ?? "Appareil"}
          </h1>
          {appliance?.category && (
            <p className="text-white/60 text-xs">{appliance.category}</p>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Info card */}
        {appliance && (
          <div className="mx-4 mt-4 bg-white rounded-xl p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-500 text-xs">Enregistre le</span>
              <span className="text-gray-700 text-xs font-medium">
                {formatDate(appliance.create_date)}
              </span>
            </div>
          </div>
        )}

        {/* Upcoming maintenance */}
        {upcoming.length > 0 && (
          <div className="mx-4 mt-3">
            <h2 className="text-gray-700 font-semibold text-sm mb-2">Entretiens a venir</h2>
            <div className="space-y-2">
              {upcoming.map((r) => (
                <div key={r.id} className="bg-orange-50 border border-orange-100 rounded-xl p-3">
                  <p className="text-gray-900 text-sm font-medium">{r.name}</p>
                  {r.schedule_date && (
                    <p className="text-[#f57c00] text-xs mt-0.5">{formatDate(r.schedule_date)}</p>
                  )}
                  {r.description && (
                    <p className="text-gray-500 text-xs mt-1">{r.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Past maintenance */}
        {past.length > 0 && (
          <div className="mx-4 mt-3">
            <h2 className="text-gray-700 font-semibold text-sm mb-2">Historique</h2>
            <div className="space-y-2">
              {past.map((r) => (
                <div key={r.id} className="bg-gray-50 rounded-xl p-3">
                  <p className="text-gray-700 text-sm">{r.name}</p>
                  {r.schedule_date && (
                    <p className="text-gray-400 text-xs mt-0.5">{formatDate(r.schedule_date)}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Per-appliance chat */}
        <div className="mx-4 mt-3 mb-2">
          <h2 className="text-gray-700 font-semibold text-sm mb-2">Conversation</h2>
          {messages.length === 0 && (
            <p className="text-gray-400 text-xs mb-2">
              Posez une question sur cet appareil.
            </p>
          )}
          <div className="space-y-1">
            {messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} content={m.content} />
            ))}
            {chatLoading && <LoadingDots />}
            <div ref={bottomRef} />
          </div>
        </div>
      </div>

      {/* Chat input */}
      <div className="bg-white border-t border-gray-100 px-3 py-2 flex-shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const text = input.trim();
            if (text && !chatLoading) sendMessage(text);
          }}
          className="flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Question sur ${appliance?.name ?? "cet appareil"}...`}
            disabled={chatLoading}
            className="flex-1 px-4 py-2.5 rounded-full bg-gray-100 text-gray-900 placeholder-gray-400 text-sm focus:outline-none focus:bg-white focus:ring-2 focus:ring-[#1a237e] transition"
          />
          <button
            type="submit"
            disabled={!input.trim() || chatLoading}
            className="w-9 h-9 bg-[#f57c00] rounded-full flex items-center justify-center disabled:opacity-40 flex-shrink-0"
          >
            <svg viewBox="0 0 24 24" fill="white" className="w-4 h-4">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
