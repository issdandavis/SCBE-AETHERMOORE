import React, { useState, useEffect } from 'react';
import {
  CloudSun,
  Sun,
  Cloud,
  CloudRain,
  CloudSnow,
  Wind,
  Droplets,
  Eye,
  Thermometer,
  MapPin,
  Loader,
} from 'lucide-react';

interface WeatherData {
  temp: number;
  feelsLike: number;
  humidity: number;
  windSpeed: number;
  visibility: number;
  condition: string;
  city: string;
  daily: { day: string; max: number; min: number; condition: string }[];
  hourly: { time: string; temp: number }[];
}

const CONDITIONS: Record<string, { icon: React.ReactNode; name: string }> = {
  '0': { icon: <Sun size={48} />, name: 'Clear' },
  '1': { icon: <CloudSun size={48} />, name: 'Mainly Clear' },
  '2': { icon: <CloudSun size={48} />, name: 'Partly Cloudy' },
  '3': { icon: <Cloud size={48} />, name: 'Overcast' },
  '45': { icon: <Cloud size={48} />, name: 'Foggy' },
  '51': { icon: <CloudRain size={48} />, name: 'Drizzle' },
  '61': { icon: <CloudRain size={48} />, name: 'Rain' },
  '71': { icon: <CloudSnow size={48} />, name: 'Snow' },
  '80': { icon: <CloudRain size={48} />, name: 'Showers' },
  '95': { icon: <CloudRain size={48} />, name: 'Thunderstorm' },
};

const CITIES = [
  { name: 'New York', lat: 40.71, lon: -74.01 },
  { name: 'London', lat: 51.51, lon: -0.13 },
  { name: 'Tokyo', lat: 35.68, lon: 139.69 },
  { name: 'Sydney', lat: -33.87, lon: 151.21 },
  { name: 'Paris', lat: 48.86, lon: 2.35 },
  { name: 'Dubai', lat: 25.2, lon: 55.27 },
  { name: 'Singapore', lat: 1.35, lon: 103.82 },
  { name: 'Berlin', lat: 52.52, lon: 13.41 },
  { name: 'Toronto', lat: 43.65, lon: -79.38 },
  { name: 'Mumbai', lat: 19.08, lon: 72.88 },
];

function getCondition(code: number) {
  const key = String(code);
  return CONDITIONS[key] || CONDITIONS['0'];
}

function getDayName(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en', { weekday: 'short' });
}

export default function Weather() {
  const [cityIdx, setCityIdx] = useState(0);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchWeather = async (idx: number) => {
    setLoading(true);
    setError('');
    try {
      const city = CITIES[idx];
      const res = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${city.lat}&longitude=${city.lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,visibility&daily=weather_code,temperature_2m_max,temperature_2m_min&hourly=temperature_2m&timezone=auto&forecast_days=5`
      );
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();

      const hourly = (data.hourly?.temperature_2m || [])
        .slice(0, 24)
        .map((t: number, i: number) => ({
          time: `${i}:00`,
          temp: Math.round(t),
        }));

      const daily = (data.daily?.time || []).slice(0, 5).map((t: string, i: number) => ({
        day: getDayName(t),
        max: Math.round(data.daily.temperature_2m_max[i]),
        min: Math.round(data.daily.temperature_2m_min[i]),
        condition: getCondition(data.daily.weather_code[i]).name,
      }));

      setWeather({
        temp: Math.round(data.current.temperature_2m),
        feelsLike: Math.round(data.current.apparent_temperature),
        humidity: data.current.relative_humidity_2m,
        windSpeed: Math.round(data.current.wind_speed_10m),
        visibility: Math.round((data.current.visibility || 10000) / 1000),
        condition: getCondition(data.current.weather_code).name,
        city: city.name,
        daily,
        hourly,
      });
    } catch (e) {
      setError('Failed to fetch weather data. Using fallback.');
      const city = CITIES[idx];
      setWeather({
        temp: 22,
        feelsLike: 20,
        humidity: 65,
        windSpeed: 12,
        visibility: 10,
        condition: 'Partly Cloudy',
        city: city.name,
        daily: [
          { day: 'Mon', max: 24, min: 18, condition: 'Clear' },
          { day: 'Tue', max: 22, min: 16, condition: 'Cloudy' },
          { day: 'Wed', max: 20, min: 15, condition: 'Rain' },
          { day: 'Thu', max: 23, min: 17, condition: 'Clear' },
          { day: 'Fri', max: 25, min: 19, condition: 'Sunny' },
        ],
        hourly: Array.from({ length: 12 }, (_, i) => ({
          time: `${i * 2}:00`,
          temp: 18 + Math.floor(Math.random() * 8),
        })),
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather(cityIdx);
  }, [cityIdx]);

  const cond = weather
    ? getCondition(
        weather.condition === 'Clear'
          ? 0
          : weather.condition === 'Partly Cloudy'
            ? 1
            : weather.condition === 'Overcast'
              ? 3
              : weather.condition === 'Rain'
                ? 61
                : 0
      )
    : getCondition(0);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 overflow-y-auto">
      <div className="flex items-center gap-2 mb-4">
        <MapPin size={14} className="text-blue-400" />
        <select
          value={cityIdx}
          onChange={(e) => setCityIdx(Number(e.target.value))}
          className="bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-1.5 text-sm outline-none flex-1"
        >
          {CITIES.map((c, i) => (
            <option key={i} value={i}>
              {c.name}
            </option>
          ))}
        </select>
        {loading && <Loader size={14} className="text-blue-400 animate-spin" />}
      </div>

      {error && (
        <div className="text-xs text-yellow-400/60 bg-yellow-500/10 rounded-lg px-3 py-1.5 mb-3">
          {error}
        </div>
      )}

      {weather && (
        <>
          <div className="text-center mb-4">
            <div className="text-blue-400 mb-2">{cond.icon}</div>
            <div className="text-5xl font-light mb-1">{weather.temp}°C</div>
            <div className="text-sm text-blue-300/50 mb-1">{weather.condition}</div>
            <div className="text-xs text-blue-300/30">Feels like {weather.feelsLike}°C</div>
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {[
              { icon: <Wind size={14} />, label: 'Wind', value: `${weather.windSpeed} km/h` },
              { icon: <Droplets size={14} />, label: 'Humidity', value: `${weather.humidity}%` },
              { icon: <Eye size={14} />, label: 'Visibility', value: `${weather.visibility} km` },
            ].map((item) => (
              <div
                key={item.label}
                className="bg-[#162032] rounded-xl p-2.5 text-center border border-blue-500/10"
              >
                <div className="text-blue-400/50 flex justify-center mb-1">{item.icon}</div>
                <div className="text-[10px] text-blue-300/30">{item.label}</div>
                <div className="text-xs text-blue-200/70 font-medium">{item.value}</div>
              </div>
            ))}
          </div>

          {/* Hourly graph */}
          <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10 mb-3">
            <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
              24-Hour Temperature
            </div>
            <div className="flex items-end gap-0.5 h-16">
              {weather.hourly.slice(0, 12).map((h, i) => {
                const maxT = Math.max(...weather.hourly.map((x) => x.temp));
                const minT = Math.min(...weather.hourly.map((x) => x.temp));
                const height = maxT === minT ? 50 : ((h.temp - minT) / (maxT - minT)) * 80 + 20;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center justify-end group">
                    <span className="text-[8px] text-blue-300/20 opacity-0 group-hover:opacity-100 transition-opacity mb-0.5">
                      {h.temp}°
                    </span>
                    <div
                      className="w-full rounded-t"
                      style={{
                        height: `${height}%`,
                        background: `linear-gradient(to top, rgba(59,130,246,0.3), rgba(59,130,246,0.6))`,
                      }}
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* 5-day forecast */}
          <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
            <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
              5-Day Forecast
            </div>
            <div className="space-y-2">
              {weather.daily.map((d, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-xs text-blue-200/50 w-8">{d.day}</span>
                  <span className="text-[10px] text-blue-300/30 flex-1 text-center">
                    {d.condition}
                  </span>
                  <div className="flex items-center gap-1">
                    <div className="w-16 h-1 bg-blue-500/10 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-blue-500/40"
                        style={{ width: `${((d.max - d.min) / 20) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-blue-200/50 w-8 text-right">{d.max}°</span>
                  <span className="text-xs text-blue-300/20 w-8 text-right">{d.min}°</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
