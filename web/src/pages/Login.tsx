import { useState } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        if (password.length < 8) {
          setError("Le mot de passe doit contenir au moins 8 caractères.");
          setLoading(false);
          return;
        }
        await signup(email, password);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Une erreur s'est produite.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-[#faf8f5] via-[#f0ded8] to-[#e8f0e9] relative">
      {/* Header bar */}
      <div className="bg-transparent py-3 text-center">
        <h1 className="text-[#c45d3e] font-black text-lg tracking-wider">HODOOR</h1>
      </div>

      {/* Floating card */}
      <div className="flex-1 flex items-center justify-center px-8">
        <div className="w-full max-w-sm bg-white/95 backdrop-blur rounded-2xl shadow-2xl px-7 py-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[11px] font-bold text-gray-500 tracking-wider uppercase mb-2">
                Email professionnel
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
                  </svg>
                </span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nom@entreprise.fr"
                  required
                  className="w-full pl-11 pr-4 py-3 rounded-xl border border-gray-200 bg-gray-50 text-gray-900 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#c45d3e] focus:bg-white transition"
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-[11px] font-bold text-gray-500 tracking-wider uppercase">
                  Mot de passe
                </label>
                {mode === "login" && (
                  <button
                    type="button"
                    className="text-[11px] text-[#c45d3e] font-bold hover:underline"
                    onClick={() => {}}
                  >
                    Oublié ?
                  </button>
                )}
              </div>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z" />
                  </svg>
                </span>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === "signup" ? "8 caractères minimum" : "••••••••"}
                  required
                  className="w-full pl-11 pr-11 py-3 rounded-xl border border-gray-200 bg-gray-50 text-gray-900 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#c45d3e] focus:bg-white transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                      <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                      <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#c45d3e] text-white font-bold py-3.5 rounded-2xl disabled:opacity-50 hover:bg-[#a84e34] transition-colors shadow-md flex items-center justify-center gap-2"
            >
              {loading ? (
                "Chargement..."
              ) : mode === "login" ? (
                <>SE CONNECTER <span className="text-lg">→</span></>
              ) : (
                "CRÉER LE COMPTE"
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "signup" : "login");
                setError("");
              }}
              className="text-[#c45d3e] text-sm font-medium hover:underline"
            >
              {mode === "login"
                ? "Pas encore de compte ? S'inscrire"
                : "Déjà un compte ? Se connecter"}
            </button>
          </div>
        </div>
      </div>

      {/* Tagline at bottom */}
      <div className="py-6 text-center">
        <p className="text-[#8a8078] text-[10px] font-semibold tracking-[0.2em] uppercase italic">
          Réparer plutôt que tout jeter.
        </p>
      </div>
    </div>
  );
}
