import { api, type Appliance, type MaintenanceRequest } from "./api";

function notificationBody(request: MaintenanceRequest, applianceName?: string): string {
  if (request.description?.trim()) {
    return request.description.trim();
  }
  if (applianceName) {
    return `Maintenance prévue pour ${applianceName}.`;
  }
  return request.name;
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function requestNotificationPermission(): Promise<NotificationPermission | "unsupported"> {
  if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return "unsupported";
  }
  if (Notification.permission === "granted") {
    return "granted";
  }
  return Notification.requestPermission();
}

export async function ensurePushSubscription() {
  const permission = await requestNotificationPermission();
  if (permission !== "granted") {
    return permission;
  }

  const registration = await navigator.serviceWorker.ready;
  const existing = await registration.pushManager.getSubscription();
  if (existing) {
    await existing.unsubscribe().catch(() => undefined);
  }
  const { public_key } = await api.push.getVapidPublicKey();
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  });

  const json = subscription.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Invalid push subscription payload.");
  }

  await api.push.subscribe({
    endpoint: json.endpoint,
    keys: {
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
    },
  });

  return "granted";
}

export async function sendTestNotification() {
  await api.push.test(
    "Rappel Hodoor",
    "Notification push envoyée depuis le serveur dans 30 secondes.",
  );
}

export async function fetchPushDebug() {
  return api.push.debug();
}

export async function syncMaintenanceNotifications() {
  const permission = await ensurePushSubscription();
  if (permission !== "granted") {
    return permission;
  }

  const appliances = await api.appliances.list();
  const upcoming = appliances.flatMap((appliance: Appliance) =>
    appliance.maintenance_requests
      .filter((request) => request.schedule_date)
      .map((request) => ({
        title: `Rappel Hodoor · ${appliance.name}`,
        body: notificationBody(request, appliance.name),
      })),
  );

  if (upcoming.length === 0) {
    return permission;
  }

  return permission;
}
