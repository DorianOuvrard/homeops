import { useAuth } from "../auth";

export default function Settings() {
  const { user, logout } = useAuth();

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-[#1a237e] px-4 py-3 flex items-center justify-center shrink-0">
        <h1 className="text-white font-bold text-lg tracking-wide">Réglages</h1>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {/* Profile */}
        <div className="bg-white rounded-2xl p-5 shadow-sm mb-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#1a237e] flex items-center justify-center text-white font-bold text-lg shrink-0">
              {user?.email?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="min-w-0">
              <p className="text-gray-900 font-semibold text-sm truncate">{user?.email}</p>
              <p className="text-gray-400 text-xs mt-0.5">Compte HODOOR</p>
            </div>
          </div>
        </div>

        {/* App info */}
        <div className="bg-white rounded-2xl shadow-sm divide-y divide-gray-100 mb-4">
          <div className="px-5 py-4 flex items-center justify-between">
            <span className="text-sm text-gray-600">Version</span>
            <span className="text-sm text-gray-400">1.0.0</span>
          </div>
          <div className="px-5 py-4 flex items-center justify-between">
            <span className="text-sm text-gray-600">Thème</span>
            <span className="text-sm text-gray-400">Clair</span>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className="w-full bg-white rounded-2xl shadow-sm px-5 py-4 text-left text-red-500 text-sm font-medium hover:bg-red-50 transition-colors"
        >
          Se déconnecter
        </button>
      </div>
    </div>
  );
}
