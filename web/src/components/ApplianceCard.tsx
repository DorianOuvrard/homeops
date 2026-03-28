import { useNavigate } from "react-router-dom";
import type { Appliance } from "../api";

interface ApplianceCardProps {
  appliance: Appliance;
}

function ApplianceIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8 text-[#1a237e]">
      <path d="M22 9V7h-2V5c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-2h2v-2h-2v-2h2v-2h-2V9h2zm-4 10H4V5h14v14z" />
      <path d="M8 15h2v2H8zm0-4h2v2H8zm0-4h2v2H8zm4 8h4v2h-4zm0-4h4v2h-4zm0-4h4v2h-4z" />
    </svg>
  );
}

export default function ApplianceCard({ appliance }: ApplianceCardProps) {
  const navigate = useNavigate();
  const upcomingCount = appliance.maintenance_requests?.filter(
    (r) => r.schedule_date && new Date(r.schedule_date) >= new Date()
  ).length ?? 0;

  return (
    <button
      onClick={() => navigate(`/scan/${appliance.id}`)}
      className="w-full bg-white rounded-xl p-4 shadow-sm flex items-center gap-3 text-left hover:shadow-md transition-shadow"
    >
      <div className="shrink-0 w-12 h-12 bg-[#e8eaf6] rounded-xl flex items-center justify-center">
        <ApplianceIcon />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-900 truncate">{appliance.name}</p>
        {appliance.category && (
          <p className="text-sm text-gray-500 truncate">{appliance.category}</p>
        )}
        {upcomingCount > 0 && (
          <p className="text-xs text-[#f57c00] mt-0.5">
            {upcomingCount} entretien{upcomingCount > 1 ? "s" : ""} a venir
          </p>
        )}
      </div>
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-gray-300 flex-shrink-0">
        <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z" />
      </svg>
    </button>
  );
}
