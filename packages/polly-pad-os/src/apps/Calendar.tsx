import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Clock, Trash2, Download, Upload } from 'lucide-react';

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

interface CalendarEvent {
  title: string;
  time?: string;
  color: string;
}
const STORAGE_KEY = 'linuxos_calendar_events';
const EVENT_COLORS = [
  'bg-blue-500/30',
  'bg-green-500/30',
  'bg-yellow-500/30',
  'bg-red-500/30',
  'bg-purple-500/30',
  'bg-pink-500/30',
];

export default function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
  const [events, setEvents] = useState<Record<string, CalendarEvent[]>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return {};
  });
  const [showEventForm, setShowEventForm] = useState(false);
  const [eventInput, setEventInput] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [eventColor, setEventColor] = useState(EVENT_COLORS[0]);
  const today = new Date();

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  }, [events]);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  const getEventKey = (d: number) => `${year}-${month}-${d}`;
  const getEventsForDate = (d: number) => events[getEventKey(d)] || [];

  const addEvent = () => {
    if (!eventInput.trim() || !selectedDate) return;
    const key = `${selectedDate.getFullYear()}-${selectedDate.getMonth()}-${selectedDate.getDate()}`;
    const newEvent: CalendarEvent = {
      title: eventInput.trim(),
      time: eventTime || undefined,
      color: eventColor,
    };
    setEvents((prev) => ({ ...prev, [key]: [...(prev[key] || []), newEvent] }));
    setEventInput('');
    setEventTime('');
    setShowEventForm(false);
  };

  const deleteEvent = (dateKey: string, index: number) => {
    setEvents((prev) => {
      const updated = { ...prev };
      updated[dateKey] = updated[dateKey].filter((_, i) => i !== index);
      if (updated[dateKey].length === 0) delete updated[dateKey];
      return updated;
    });
  };

  const exportEvents = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `calendar-events-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importEvents = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const imported = JSON.parse(ev.target?.result as string);
          if (typeof imported === 'object') setEvents((prev) => ({ ...prev, ...imported }));
        } catch {
          /* ignore */
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const upcomingEvents = Object.entries(events)
    .flatMap(([key, evs]) => evs.map((e) => ({ ...e, date: key })))
    .slice(0, 5);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">
            {MONTHS[month]} {year}
          </h2>
          <div className="flex gap-0.5">
            <button
              onClick={prevMonth}
              className="p-1 rounded hover:bg-blue-500/20 transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={nextMonth}
              className="p-1 rounded hover:bg-blue-500/20 transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={importEvents}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
            title="Import"
          >
            <Upload size={13} />
          </button>
          <button
            onClick={exportEvents}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
            title="Export"
          >
            <Download size={13} />
          </button>
          <button
            onClick={() => {
              setCurrentDate(new Date());
              setSelectedDate(new Date());
            }}
            className="text-xs px-3 py-1 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 transition-colors"
          >
            Today
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 border-b border-blue-500/10">
        {DAYS.map((d) => (
          <div
            key={d}
            className="text-center py-2 text-[10px] uppercase tracking-wider text-blue-400/30 font-semibold"
          >
            {d}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 flex-1">
        {Array.from({ length: firstDay }).map((_, i) => (
          <div key={`e${i}`} className="border-r border-b border-blue-500/5" />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const isToday =
            day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
          const isSelected =
            selectedDate &&
            day === selectedDate.getDate() &&
            month === selectedDate.getMonth() &&
            year === selectedDate.getFullYear();
          const dayEvents = getEventsForDate(day);
          return (
            <button
              key={day}
              onClick={() => setSelectedDate(new Date(year, month, day))}
              className={`border-r border-b border-blue-500/5 p-1 text-left transition-all hover:bg-blue-500/5 ${isSelected ? 'bg-blue-500/10' : ''} ${isToday ? 'ring-1 ring-inset ring-blue-500/30' : ''}`}
            >
              <span
                className={`text-xs ${isToday ? 'text-blue-400 font-bold' : 'text-blue-200/50'}`}
              >
                {day}
              </span>
              {dayEvents.length > 0 && (
                <div className="mt-0.5 space-y-0.5">
                  {dayEvents.slice(0, 2).map((e, ei) => (
                    <div
                      key={ei}
                      className={`text-[9px] ${e.color} text-blue-200/70 px-1 rounded truncate`}
                    >
                      {e.time ? `${e.time} ` : ''}
                      {e.title}
                    </div>
                  ))}
                  {dayEvents.length > 2 && (
                    <div className="text-[9px] text-blue-400/40 px-1">
                      +{dayEvents.length - 2} more
                    </div>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {selectedDate && (
        <div className="border-t border-blue-500/10 p-3 bg-[#111d2e]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm text-blue-200">
              <Clock size={14} className="text-blue-400" />
              {selectedDate.toLocaleDateString('en', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </div>
            <button
              onClick={() => setShowEventForm(!showEventForm)}
              className="text-xs px-2 py-1 rounded bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 transition-colors"
            >
              + Add Event
            </button>
          </div>
          {showEventForm && (
            <div className="flex gap-2 mb-2 flex-wrap">
              <input
                type="text"
                value={eventInput}
                onChange={(e) => setEventInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addEvent()}
                placeholder="Event name..."
                className="flex-1 min-w-[120px] bg-[#162032] border border-blue-500/15 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500/30"
                autoFocus
              />
              <input
                type="time"
                value={eventTime}
                onChange={(e) => setEventTime(e.target.value)}
                className="bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1.5 text-xs outline-none"
              />
              <div className="flex gap-1">
                {EVENT_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setEventColor(c)}
                    className={`w-5 h-5 rounded-full ${c} ${eventColor === c ? 'ring-2 ring-white' : ''}`}
                  />
                ))}
              </div>
              <button
                onClick={addEvent}
                className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 text-xs transition-colors"
              >
                Add
              </button>
            </div>
          )}
          <div className="space-y-1 max-h-24 overflow-y-auto">
            {getEventsForDate(selectedDate.getDate()).map((e, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <span className={`w-1.5 h-1.5 rounded-full ${e.color}`} />
                {e.time && <span className="text-[10px] text-blue-400/40 font-mono">{e.time}</span>}
                <span className="text-xs text-blue-200/50 flex-1">{e.title}</span>
                <button
                  onClick={() => deleteEvent(getEventKey(selectedDate.getDate()), i)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/20 text-red-400 transition-all"
                >
                  <Trash2 size={9} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
