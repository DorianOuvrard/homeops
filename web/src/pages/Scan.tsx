import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, type Appliance, type ChatMessage } from "../api";
import { useAppContext } from "../AppContext";
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
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { setPendingChatMessage } = useAppContext();

  const refreshAppliances = () => {
    api.appliances
      .list()
      .then(setAppliances)
      .catch(() => setError("Impossible de charger les appareils."))
      .finally(() => setLoadingAppliances(false));
  };

  const location = useLocation();
  useEffect(() => {
    if (location.pathname === "/scan") {
      refreshAppliances();
    }
  }, [location.pathname]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loadingChat]);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 960 } },
      });
      streamRef.current = stream;
      setCameraActive(true);
    } catch {
      // Camera not available, fall back to file picker
      fileRef.current?.click();
    }
  }, []);

  // Assign stream to video element after React renders it
  useEffect(() => {
    if (cameraActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraActive]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  }, []);

  // Stop camera when navigating away (persistent tab stays mounted)
  useEffect(() => {
    if (location.pathname !== "/scan") {
      stopCamera();
    }
    return () => { stopCamera(); };
  }, [location.pathname, stopCamera]);

  const capturePhoto = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    stopCamera();

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], "scan.jpg", { type: "image/jpeg" });
        sendScanPhoto(file);
      }
    }, "image/jpeg", 0.85);
  }, [stopCamera]);

  const sendScanPhoto = async (file: File) => {
    const imageUrl = URL.createObjectURL(file);
    const userMsg = {
      role: "user" as const,
      content: "",
      imageUrl,
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

  const triggerScan = () => {
    if (cameraActive) {
      capturePhoto();
    } else {
      startCamera();
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#faf8f5] relative">
      {/* Fullscreen camera overlay */}
      {cameraActive && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="flex-1 w-full object-cover"
          />
          {/* Viewfinder brackets */}
          <div className="absolute inset-12 pointer-events-none">
            <div className="absolute top-0 left-0 w-8 h-8 border-t-3 border-l-3 border-white/70 rounded-tl" />
            <div className="absolute top-0 right-0 w-8 h-8 border-t-3 border-r-3 border-white/70 rounded-tr" />
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b-3 border-l-3 border-white/70 rounded-bl" />
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b-3 border-r-3 border-white/70 rounded-br" />
          </div>
          <div className="absolute bottom-12 left-0 right-0 flex items-center justify-center gap-6">
            <button
              onClick={stopCamera}
              className="w-12 h-12 rounded-full bg-black/50 flex items-center justify-center"
            >
              <svg viewBox="0 0 24 24" fill="white" className="w-6 h-6">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
              </svg>
            </button>
            <button
              onClick={capturePhoto}
              className="w-18 h-18 rounded-full border-4 border-white flex items-center justify-center"
            >
              <div className="w-14 h-14 rounded-full bg-white" />
            </button>
            <div className="w-12 h-12" />
          </div>
        </div>
      )}

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />
      <canvas ref={canvasRef} className="hidden" />

      <div className="flex-1 overflow-y-auto">
        {/* Scan button card */}
        <div className="px-4 pt-5">
          <button
            onClick={triggerScan}
            disabled={loadingChat}
            className="w-full bg-white rounded-2xl shadow-sm px-5 py-4 flex items-center gap-4 hover:shadow-md transition-shadow disabled:opacity-50 text-left border border-[#f0ece7]"
          >
            <div className="w-12 h-12 bg-[#c45d3e] rounded-xl flex items-center justify-center shrink-0">
              <svg viewBox="0 0 24 24" fill="white" className="w-6 h-6">
                <path d="M3 11h8V3H3v8zm2-6h4v4H5V5zm8-2v8h8V3h-8zm6 6h-4V5h4v4zM3 21h8v-8H3v8zm2-6h4v4H5v-4zm13-2h-2v3h-3v2h3v3h2v-3h3v-2h-3v-3z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-bold text-[#3d3833]">Scanner un appareil</p>
              <p className="text-xs text-gray-400 font-semibold tracking-wide uppercase">
                {loadingChat ? (
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-[#d4915e] rounded-full animate-pulse" />
                    Analyse en cours...
                  </span>
                ) : (
                  "Photo ou caméra"
                )}
              </p>
            </div>
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-gray-300 shrink-0">
              <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4z" />
              <path d="M9 3L7.17 5H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2h-3.17L15 3H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" />
            </svg>
          </button>
        </div>

        {/* Chat messages from scan */}
        {messages.length > 0 && (
          <div className="px-4 pt-4 pb-2 space-y-1">
            {messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} content={m.content} imageUrl={(m as { imageUrl?: string }).imageUrl} />
            ))}
            {loadingChat && <LoadingDots />}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Follow-up text input */}
        {messages.length > 0 && (
          <div className="px-4 pb-3">
            <div className="flex items-center gap-2 bg-white rounded-full px-4 py-1.5 shadow-sm border border-[#f0ece7]">
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
                className="flex-1 min-w-0 py-2 text-[#3d3833] placeholder-gray-400 text-sm bg-transparent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => {
                  const text = input.trim();
                  if (text && !loadingChat) sendText(text);
                }}
                disabled={!input.trim() || loadingChat}
                className="w-9 h-9 bg-[#c45d3e] rounded-full flex items-center justify-center disabled:opacity-40 shrink-0 hover:bg-[#a84e34] transition-colors"
              >
                <svg viewBox="0 0 24 24" fill="white" className="w-4 h-4">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Appliance list */}
        <div className="px-4 pt-5 pb-20">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[#3d3833] font-bold text-sm uppercase tracking-wide">
              Historique récent
            </h2>
            {appliances.length > 0 && (
              <span className="text-[#c45d3e] text-sm font-semibold">Tout voir</span>
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

      {/* Floating "Generate plan" button */}
      {appliances.length >= 3 && !loadingChat && (
        <div className="absolute bottom-2 left-3 right-3 z-20">
          <button
            onClick={() => {
              setPendingChatMessage("J'ai fini, fais le récap et le plan de prévention");
              navigate("/chat");
            }}
            className="w-full bg-[#c45d3e] text-white rounded-xl py-3.5 font-semibold text-sm shadow-lg flex items-center justify-center gap-2 hover:bg-[#a84e34] transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
            </svg>
            Générer mon plan d'entretien
          </button>
        </div>
      )}

    </div>
  );
}
