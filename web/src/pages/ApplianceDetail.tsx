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

const ALLOWED_TAGS = new Set(["b", "strong", "i", "em", "p", "br", "ul", "ol", "li", "h3", "h4"]);

function sanitizeHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  function clean(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const el = node as Element;
    const tag = el.tagName.toLowerCase();
    const inner = Array.from(el.childNodes).map(clean).join("");
    if (ALLOWED_TAGS.has(tag)) return `<${tag}>${inner}</${tag}>`;
    return inner;
  }
  return Array.from(doc.body.childNodes).map(clean).join("");
}

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
      <span className="text-gray-400 text-xs">{label}</span>
      <span className="text-gray-700 text-xs font-medium text-right max-w-[60%] truncate">{value}</span>
    </div>
  );
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

  const warrantyActive = appliance?.warranty_date && new Date(appliance.warranty_date) >= new Date();

  return (
    <div className="flex flex-col h-full">
      {/* Header with image */}
      <div className="bg-[#1a237e] px-4 py-3 flex items-center gap-3 flex-shrink-0">
        <button onClick={() => navigate("/scan")} className="text-white/70 hover:text-white">
          <BackIcon />
        </button>
        {appliance?.image_128 && (
          <img
            src={appliance.image_128}
            alt={appliance.name}
            className="w-10 h-10 rounded-lg object-cover border-2 border-white/20"
          />
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-white font-bold text-base leading-tight truncate">
            {appliance?.name ?? "Appareil"}
          </h1>
          <div className="flex items-center gap-2">
            {appliance?.category && (
              <span className="text-white/60 text-xs">{appliance.category}</span>
            )}
            {appliance?.model && (
              <span className="text-white/40 text-xs">{appliance.model}</span>
            )}
          </div>
        </div>
        {warrantyActive && (
          <span className="shrink-0 bg-green-500/20 text-green-300 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
            Garantie
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Product info card */}
        {appliance && (
          <div className="mx-4 mt-4 bg-white rounded-xl p-4 shadow-sm">
            <h2 className="text-gray-800 font-semibold text-sm mb-2">Fiche produit</h2>
            <InfoRow label="Modèle" value={appliance.model} />
            <InfoRow label="N° série" value={appliance.serial_no} />
            <InfoRow label="Fabricant" value={appliance.vendor} />
            <InfoRow label="Réf. fournisseur" value={appliance.vendor_ref} />
            <InfoRow label="Coût" value={appliance.cost ? `${appliance.cost.toFixed(0)} €` : null} />
            <InfoRow label="Emplacement" value={appliance.location} />
            <InfoRow label="Date d'acquisition" value={formatDate(appliance.effective_date)} />
            <InfoRow label="Fin de garantie" value={formatDate(appliance.warranty_date)} />
            <InfoRow label="Enregistré le" value={formatDate(appliance.create_date)} />
            {!appliance.model && !appliance.serial_no && !appliance.vendor && !appliance.cost && (
              <p className="text-gray-300 text-xs italic py-1">Aucun détail renseigné</p>
            )}
          </div>
        )}

        {/* Note / description */}
        {appliance?.note && (
          <div className="mx-4 mt-3 bg-white rounded-xl p-4 shadow-sm">
            <h2 className="text-gray-800 font-semibold text-sm mb-2">Description & entretien</h2>
            <div
              className="text-gray-600 text-xs leading-relaxed [&_b]:font-semibold [&_b]:text-gray-700 [&_ul]:list-disc [&_ul]:ml-4 [&_ul]:mt-1 [&_ol]:list-decimal [&_ol]:ml-4 [&_ol]:mt-1 [&_li]:mt-0.5 [&_p]:mt-1 first:[&_p]:mt-0"
              dangerouslySetInnerHTML={{ __html: sanitizeHtml(appliance.note) }}
            />
          </div>
        )}

        {/* Upcoming maintenance */}
        {upcoming.length > 0 && (
          <div className="mx-4 mt-3">
            <h2 className="text-gray-700 font-semibold text-sm mb-2">Entretiens à venir</h2>
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
