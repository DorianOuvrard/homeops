import { useAuth } from "../auth";
import { useState } from "react";
import {
  ensurePushSubscription,
  fetchPushDebug,
  sendTestNotification,
} from "../notifications";

export default function Settings() {
  const { user, logout } = useAuth();
  const [notificationState, setNotificationState] = useState<string>("Non configurées");
  const [subscriptionCount, setSubscriptionCount] = useState<number | null>(null);

  const enableNotifications = async () => {
    const result = await ensurePushSubscription();
    if (result === "unsupported") {
      setNotificationState("Notifications non supportées sur cet appareil.");
      return;
    }
    if (result === "granted") {
      const debug = await fetchPushDebug();
      setSubscriptionCount(debug.count);
    }
    setNotificationState(
      result === "granted"
        ? "Notifications activées et abonnement push enregistré."
        : "Permission refusée. Activez-les dans le navigateur.",
    );
  };

  const testNotifications = async () => {
    await sendTestNotification();
    const debug = await fetchPushDebug();
    setSubscriptionCount(debug.count);
    setNotificationState("Notification programmée, elle arrivera dans 30 secondes.");
  };

  return (
    <div className="flex flex-col h-full bg-[#faf8f5]">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {/* Profile */}
        <div className="bg-white rounded-2xl p-5 shadow-sm mb-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#c45d3e] flex items-center justify-center text-white font-bold text-lg shrink-0">
              {user?.email?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="min-w-0">
              <p className="text-[#3d3833] font-semibold text-sm truncate">{user?.email}</p>
              <p className="text-gray-400 text-xs mt-0.5">Compte Hodoor</p>
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

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-[#3d3833]">Notifications PWA</p>
              <p className="text-xs text-gray-500 mt-1">
                Push serveur envoyés vers votre appareil, même si la PWA n'est pas ouverte.
              </p>
              <p className="text-xs text-[#c45d3e] mt-3">{notificationState}</p>
              <p className="text-xs text-gray-400 mt-1">
                Souscriptions actives : {subscriptionCount ?? "inconnues"}
              </p>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={enableNotifications}
              className="rounded-2xl bg-[#c45d3e] px-4 py-2.5 text-sm font-medium text-white"
            >
              Activer
            </button>
            <button
              onClick={testNotifications}
              className="rounded-xl bg-gray-100 px-4 py-2.5 text-sm font-medium text-gray-700"
            >
              Envoyer notif
            </button>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className="w-full bg-white rounded-2xl shadow-sm px-5 py-4 text-left text-[#c45d5d] text-sm font-medium hover:bg-[#faf0ef] transition-colors"
        >
          Se déconnecter
        </button>
      </div>
    </div>
  );
}
