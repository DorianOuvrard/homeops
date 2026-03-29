import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, type MaintenanceTask, type MaintenanceStage } from "../api";
import { useAppContext } from "../AppContext";

type TimeGroup = "overdue" | "thisWeek" | "thisMonth" | "later" | "unplanned";

const GROUP_CONFIG: Record<TimeGroup, { label: string; accent: string }> = {
  overdue: { label: "En retard", accent: "text-red-500" },
  thisWeek: { label: "Cette semaine", accent: "text-[#f57c00]" },
  thisMonth: { label: "Ce mois-ci", accent: "text-[#f57c00]/70" },
  later: { label: "Plus tard", accent: "text-gray-400" },
  unplanned: { label: "Non planifié", accent: "text-gray-400" },
};

const GROUP_ORDER: TimeGroup[] = ["overdue", "thisWeek", "thisMonth", "later", "unplanned"];

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function endOfWeek(d: Date): Date {
  const day = d.getDay();
  const diff = day === 0 ? 0 : 7 - day;
  const end = new Date(d.getFullYear(), d.getMonth(), d.getDate() + diff, 23, 59, 59);
  return end;
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
  if (diffDays < -1) return `Il y a ${Math.abs(diffDays)} jours`;
  if (diffDays <= 6) return `Dans ${diffDays} jours`;
  if (diffDays <= 13) return "La semaine prochaine";
  const weeks = Math.round(diffDays / 7);
  if (weeks <= 4) return `Dans ${weeks} semaines`;
  return new Date(dateStr).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
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
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [setMaintenanceBadge]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Re-fetch when tab becomes visible
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <span className="text-gray-400 text-sm">Chargement...</span>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 px-8 text-center">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 text-gray-300">
            <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <p className="text-gray-700 font-semibold text-base">Aucun entretien prévu</p>
        <p className="text-gray-400 text-sm mt-1">
          Vos tâches de maintenance apparaîtront ici.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="px-4 pt-5 pb-4 space-y-5">
        {GROUP_ORDER.map((groupKey) => {
          const groupTasks = grouped.get(groupKey);
          if (!groupTasks || groupTasks.length === 0) return null;
          const config = GROUP_CONFIG[groupKey];

          return (
            <div key={groupKey}>
              <h2 className={`text-xs font-bold uppercase tracking-wide mb-2 ${config.accent}`}>
                {config.label}
              </h2>
              <div className="space-y-2">
                {groupTasks.map((task) => (
                  <div
                    key={task.id}
                    className={`bg-white rounded-xl p-4 shadow-sm border ${
                      groupKey === "overdue" ? "border-red-100" : "border-gray-100"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-gray-900 font-medium text-sm">{task.name}</p>
                        {task.equipment_name && (
                          <p className="text-gray-400 text-xs mt-0.5">{task.equipment_name}</p>
                        )}
                        <div className="flex items-center gap-2 mt-1.5">
                          {task.schedule_date && (
                            <span className={`text-xs font-medium ${
                              groupKey === "overdue" ? "text-red-500" : "text-[#f57c00]"
                            }`}>
                              {formatRelative(task.schedule_date)}
                            </span>
                          )}
                          {task.maintenance_type && (
                            <span className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full ${
                              task.maintenance_type === "preventive"
                                ? "bg-blue-50 text-blue-500"
                                : "bg-orange-50 text-orange-500"
                            }`}>
                              {task.maintenance_type === "preventive" ? "préventif" : "correctif"}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => postpone(task)}
                          className="w-8 h-8 rounded-full flex items-center justify-center text-gray-300 hover:text-[#f57c00] hover:bg-orange-50 transition-colors"
                          title="Reporter d'une semaine"
                        >
                          <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                            <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" />
                          </svg>
                        </button>
                        {repairedStageId && (
                          <button
                            onClick={() => markDone(task.id)}
                            className="w-8 h-8 rounded-full flex items-center justify-center text-gray-300 hover:text-green-500 hover:bg-green-50 transition-colors"
                            title="Marquer comme fait"
                          >
                            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
