import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, type MaintenanceTask, type MaintenanceStage } from "../api";
import { useAppContext } from "../AppContext";
import {
  Wrench, AirVent, WashingMachine, Refrigerator, CookingPot, Flame,
  DoorOpen, Fence, Zap, Droplets, Tv, Wifi, Fan, Heater, Blinds,
  Shield, AlertTriangle,
  type LucideIcon,
} from "lucide-react";

type TimeGroup = "overdue" | "thisWeek" | "thisMonth" | "later" | "unplanned";

const GROUP_CONFIG: Record<TimeGroup, { label: string; accent: string }> = {
  overdue: { label: "En retard", accent: "text-[#c45d5d]" },
  thisWeek: { label: "Cette semaine", accent: "text-[#d4915e]" },
  thisMonth: { label: "Ce mois-ci", accent: "text-[#d4915e]/70" },
  later: { label: "Plus tard", accent: "text-[#8a837b]" },
  unplanned: { label: "Non planifié", accent: "text-[#8a837b]" },
};

const GROUP_ORDER: TimeGroup[] = ["overdue", "thisWeek", "thisMonth", "later", "unplanned"];

// Category icons (Lucide) from equipment name keywords
const CATEGORY_ICONS: [string[], LucideIcon][] = [
  [["climatiseur", "climatisation", "clim"], AirVent],
  [["ventil", "fan", "extracteur"], Fan],
  [["chauffage", "radiateur"], Heater],
  [["lave", "machine à laver"], WashingMachine],
  [["frigo", "réfrig", "congél"], Refrigerator],
  [["four", "micro", "plaque", "hotte", "cuisin"], CookingPot],
  [["chauffe-eau", "ballon", "cumulus"], Flame],
  [["portail", "porte", "serrure"], DoorOpen],
  [["volet", "store", "fenêtre"], Blinds],
  [["tondeuse", "jardin", "arrosage", "piscine", "clôture"], Fence],
  [["électr", "prise", "tableau", "disjoncteur"], Zap],
  [["robinet", "plomb", "fuite", "tuyau", "siphon"], Droplets],
  [["tv", "télé", "écran", "projecteur"], Tv],
  [["wifi", "routeur", "box", "réseau"], Wifi],
];

function getCategoryIcon(equipmentName: string | undefined): LucideIcon {
  if (!equipmentName) return Wrench;
  const lower = equipmentName.toLowerCase();
  for (const [keywords, icon] of CATEGORY_ICONS) {
    if (keywords.some((kw) => lower.includes(kw))) return icon;
  }
  return Wrench;
}

function cleanEquipmentName(name: string | undefined): string {
  if (!name) return "";
  // Strip serial/model refs like "/2450781-03" or "/ATL-2024-08812"
  return name.replace(/\/[\w-]+$/, "").trim();
}

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function endOfWeek(d: Date): Date {
  const day = d.getDay();
  const diff = day === 0 ? 0 : 7 - day;
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + diff, 23, 59, 59);
}

function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59);
}

function classifyDate(dateStr: string | undefined): TimeGroup {
  if (!dateStr) return "unplanned";
  const date = startOfDay(new Date(dateStr));
  const today = startOfDay(new Date());
  if (date < today) return "overdue";
  if (date <= endOfWeek(today)) return "thisWeek";
  if (date <= endOfMonth(today)) return "thisMonth";
  return "later";
}

function formatRelative(dateStr: string): string {
  const date = startOfDay(new Date(dateStr));
  const today = startOfDay(new Date());
  const diffMs = date.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Aujourd'hui";
  if (diffDays === 1) return "Demain";
  if (diffDays === -1) return "Hier";
  if (diffDays < -1) return `Il y a ${Math.abs(diffDays)}j`;
  if (diffDays <= 6) return `Dans ${diffDays}j`;
  if (diffDays <= 13) return "Sem. prochaine";
  const weeks = Math.round(diffDays / 7);
  if (weeks <= 4) return `Dans ${weeks} sem.`;
  return new Date(dateStr).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function groupTasks(tasks: MaintenanceTask[]): Map<TimeGroup, MaintenanceTask[]> {
  const groups = new Map<TimeGroup, MaintenanceTask[]>();
  for (const task of tasks) {
    const group = classifyDate(task.schedule_date);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(task);
  }
  return groups;
}

function countThisWeekTasks(tasks: MaintenanceTask[]): number {
  const today = startOfDay(new Date());
  const weekEnd = endOfWeek(today);
  return tasks.filter((t) => {
    if (!t.schedule_date) return false;
    const d = startOfDay(new Date(t.schedule_date));
    return d >= today && d <= weekEnd;
  }).length;
}

// ── Health score ───────────────────────────────────────────────────

function computeHealthScore(tasks: MaintenanceTask[]): number {
  if (tasks.length === 0) return 100;
  let penalty = 0;
  for (const t of tasks) {
    const group = classifyDate(t.schedule_date);
    if (group === "overdue") penalty += 20;
    else if (group === "thisWeek") penalty += 8;
    else if (group === "thisMonth") penalty += 4;
    else penalty += 2; // later + unplanned still count
  }
  return Math.max(0, Math.min(100, 100 - penalty));
}

function getScoreColor(score: number): string {
  if (score >= 80) return "#7a9e7e"; // sauge
  if (score >= 50) return "#d4915e"; // warm amber
  return "#c45d5d"; // warm red
}

function getScoreMessage(score: number): string {
  if (score >= 90) return "Votre maison est en pleine forme";
  if (score >= 70) return "Quelques tâches à prévoir";
  if (score >= 50) return "Attention, du retard s'accumule";
  return "Votre maison a besoin d'attention";
}

function HealthRing({ score }: { score: number }) {
  const radius = 40;
  const stroke = 6;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <div className="relative w-24 h-24">
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#f0ece7" strokeWidth={stroke} />
        <circle
          cx="50" cy="50" r={radius} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-[#3d3833]">{score}</span>
      </div>
    </div>
  );
}

// ── Swipeable card ─────────────────────────────────────────────────

const SWIPE_THRESHOLD = 80;

function SwipeCard({
  children,
  onSwipeLeft,
  onSwipeRight,
  canSwipeRight = true,
}: {
  children: React.ReactNode;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  canSwipeRight?: boolean;
}) {
  const startX = useRef(0);
  const currentX = useRef(0);
  const cardRef = useRef<HTMLDivElement>(null);
  const swiping = useRef(false);

  const handleStart = (x: number) => {
    startX.current = x;
    currentX.current = 0;
    swiping.current = true;
    if (cardRef.current) cardRef.current.style.transition = "none";
  };

  const handleMove = (x: number) => {
    if (!swiping.current) return;
    const delta = x - startX.current;
    // Limit swipe range and apply resistance
    const clamped = Math.sign(delta) * Math.min(Math.abs(delta), 140);
    // Block right swipe if can't mark done
    if (clamped > 0 && !canSwipeRight) return;
    currentX.current = clamped;
    if (cardRef.current) {
      cardRef.current.style.transform = `translateX(${clamped}px)`;
    }
  };

  const handleEnd = () => {
    if (!swiping.current) return;
    swiping.current = false;
    const delta = currentX.current;
    if (cardRef.current) {
      cardRef.current.style.transition = "transform 0.3s ease-out";
      cardRef.current.style.transform = "translateX(0)";
    }
    if (delta > SWIPE_THRESHOLD && canSwipeRight) {
      onSwipeRight();
    } else if (delta < -SWIPE_THRESHOLD) {
      onSwipeLeft();
    }
  };

  return (
    <div className="relative overflow-hidden rounded-xl">
      {/* Background actions revealed on swipe */}
      <div className="absolute inset-0 flex">
        <div className="flex-1 bg-[#7a9e7e] flex items-center pl-5">
          <span className="text-white text-xs font-semibold">Fait</span>
        </div>
        <div className="flex-1 bg-[#d4915e] flex items-center justify-end pr-5">
          <span className="text-white text-xs font-semibold">+7 jours</span>
        </div>
      </div>
      <div
        ref={cardRef}
        onTouchStart={(e) => handleStart(e.touches[0].clientX)}
        onTouchMove={(e) => handleMove(e.touches[0].clientX)}
        onTouchEnd={handleEnd}
        onMouseDown={(e) => handleStart(e.clientX)}
        onMouseMove={(e) => { if (swiping.current) handleMove(e.clientX); }}
        onMouseUp={handleEnd}
        onMouseLeave={() => { if (swiping.current) handleEnd(); }}
        className="relative cursor-grab active:cursor-grabbing"
      >
        {children}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────

export default function Maintenance() {
  const [tasks, setTasks] = useState<MaintenanceTask[]>([]);
  const [stages, setStages] = useState<MaintenanceStage[]>([]);
  const [loading, setLoading] = useState(true);
  const { setMaintenanceBadge } = useAppContext();
  const location = useLocation();

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([api.maintenance.list(), api.maintenance.stages()])
      .then(([taskList, stageList]) => {
        setTasks(taskList);
        setStages(stageList);
        setMaintenanceBadge(countThisWeekTasks(taskList));
      })
      .catch((err) => console.error("[Maintenance] fetch error:", err))
      .finally(() => setLoading(false));
  }, [setMaintenanceBadge]);

  useEffect(() => {
    if (location.pathname === "/maintenance") {
      fetchData();
    }
  }, [location.pathname, fetchData]);

  const repairedStageId = stages.find(
    (s) => s.name.toLowerCase().includes("repair") || s.name.toLowerCase().includes("réparé"),
  )?.id;

  const markDone = async (taskId: number) => {
    if (!repairedStageId) return;
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    try {
      await api.maintenance.update(taskId, { stage_id: repairedStageId });
    } catch {
      fetchData();
    }
  };

  const postpone = async (task: MaintenanceTask) => {
    const current = task.schedule_date ? new Date(task.schedule_date) : new Date();
    const next = new Date(current);
    next.setDate(next.getDate() + 7);
    const newDate = next.toISOString().split("T")[0];

    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, schedule_date: newDate } : t)),
    );
    try {
      await api.maintenance.update(task.id, { schedule_date: newDate });
    } catch {
      fetchData();
    }
  };

  const grouped = groupTasks(tasks);
  const healthScore = computeHealthScore(tasks);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#faf8f5]">
        <span className="text-[#8a837b] text-sm">Chargement...</span>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#faf8f5] px-8 text-center">
        <HealthRing score={100} />
        <p className="text-[#5a524b] font-semibold text-lg mt-5">Maison au top</p>
        <p className="text-[#8a837b] text-sm mt-1.5 max-w-[260px] leading-relaxed">
          Aucun entretien planifié. Scannez vos appareils puis générez un plan de prévention.
        </p>
        <div className="mt-8 flex items-center gap-3 text-[#8a837b]">
          <div className="flex items-center gap-1.5 text-xs">
            <Shield className="w-3.5 h-3.5 text-[#7a9e7e]" />
            <span>Préventif</span>
          </div>
          <span className="text-[#e0dbd5]">|</span>
          <div className="flex items-center gap-1.5 text-xs">
            <AlertTriangle className="w-3.5 h-3.5 text-[#d4915e]" />
            <span>Correctif</span>
          </div>
        </div>
      </div>
    );
  }

  const overdueCount = grouped.get("overdue")?.length ?? 0;
  const weekCount = grouped.get("thisWeek")?.length ?? 0;
  const totalUpcoming = tasks.length;

  return (
    <div className="h-full overflow-y-auto bg-[#faf8f5]">
      <div className="px-4 pt-5 pb-4 space-y-5">
        {/* Health score header */}
        <div className="flex items-center gap-5 bg-white rounded-2xl p-4 shadow-md">
          <HealthRing score={healthScore} />
          <div className="flex-1 min-w-0">
            <p className="text-[#3d3833] font-semibold text-sm">{getScoreMessage(healthScore)}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
              {overdueCount > 0 && (
                <span className="text-xs text-[#c45d5d] font-medium">{overdueCount} en retard</span>
              )}
              {weekCount > 0 && (
                <span className="text-xs text-[#d4915e] font-medium">{weekCount} cette sem.</span>
              )}
              <span className="text-xs text-[#8a837b]">{totalUpcoming} au total</span>
            </div>
          </div>
        </div>

        {/* Task groups */}
        {GROUP_ORDER.map((groupKey) => {
          const tasks = grouped.get(groupKey);
          if (!tasks || tasks.length === 0) return null;
          const config = GROUP_CONFIG[groupKey];

          return (
            <div key={groupKey}>
              <h2 className={`text-xs font-bold uppercase tracking-wide mb-2 ${config.accent}`}>
                {config.label}
              </h2>
              <div className="space-y-2">
                {tasks.map((task) => {
                  const Icon = getCategoryIcon(task.equipment_name);
                  const equipName = cleanEquipmentName(task.equipment_name);

                  return (
                    <SwipeCard
                      key={task.id}
                      onSwipeRight={() => markDone(task.id)}
                      onSwipeLeft={() => postpone(task)}
                      canSwipeRight={!!repairedStageId}
                    >
                      <div
                        className={`bg-white p-4 shadow-sm rounded-2xl select-none ${
                          groupKey === "overdue" ? "border border-[#f0d5d5] bg-[#faf0ef]" : ""
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                            groupKey === "overdue" ? "bg-[#faf0ef]" : "bg-[#f0ece7]"
                          }`}>
                            <Icon className={`w-[18px] h-[18px] ${
                              groupKey === "overdue" ? "text-[#c45d5d]" : "text-[#8a837b]"
                            }`} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-[#3d3833] font-medium text-sm leading-snug">{task.name}</p>
                            {equipName && (
                              <p className="text-[#8a837b] text-xs mt-0.5">{equipName}</p>
                            )}
                            <div className="flex items-center gap-2 mt-1.5">
                              {task.schedule_date && (
                                <span className={`text-xs font-medium ${
                                  groupKey === "overdue" ? "text-[#c45d5d]" : "text-[#d4915e]"
                                }`}>
                                  {formatRelative(task.schedule_date)}
                                </span>
                              )}
                              {task.maintenance_type && (
                                <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full ${
                                  task.maintenance_type === "preventive"
                                    ? "bg-[#e8f0e9] text-[#5a8a60]"
                                    : "bg-[#f0ded8] text-[#c45d3e]"
                                }`}>
                                  {task.maintenance_type === "preventive"
                                    ? <><Shield className="w-2.5 h-2.5" />préventif</>
                                    : <><AlertTriangle className="w-2.5 h-2.5" />correctif</>
                                  }
                                </span>
                              )}
                            </div>
                          </div>
                          {/* Action buttons (alternative to swipe) */}
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={(e) => { e.stopPropagation(); postpone(task); }}
                              className="w-8 h-8 rounded-full flex items-center justify-center text-[#8a837b] hover:bg-[#f0ece7] transition-colors"
                              title="Reporter +7j"
                            >
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                                <path d="M9 12l2 2 4-4" /><circle cx="12" cy="12" r="10" opacity="0" /><path d="M12 8v4l2 2" /><circle cx="12" cy="12" r="9" />
                              </svg>
                            </button>
                            {repairedStageId && (
                              <button
                                onClick={(e) => { e.stopPropagation(); markDone(task.id); }}
                                className="w-8 h-8 rounded-full flex items-center justify-center text-[#7a9e7e] hover:bg-[#e8f0e9] transition-colors"
                                title="Fait"
                              >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-4 h-4">
                                  <path d="M5 13l4 4L19 7" />
                                </svg>
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </SwipeCard>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
