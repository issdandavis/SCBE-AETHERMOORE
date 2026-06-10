import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Camera, CircleStop, Trash2, Download, SwitchCamera } from 'lucide-react';

interface Photo {
  id: string;
  dataUrl: string;
  date: number;
}

export default function CameraApp() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [photos, setPhotos] = useState<Photo[]>(() => {
    try {
      const saved = localStorage.getItem('linuxos_camera_photos');
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [];
  });
  const [error, setError] = useState('');
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');
  const [isCapturing, setIsCapturing] = useState(false);

  useEffect(() => {
    localStorage.setItem('linuxos_camera_photos', JSON.stringify(photos.slice(0, 20)));
  }, [photos]);

  const startCamera = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      setStream(s);
      if (videoRef.current) videoRef.current.srcObject = s;
      setError('');
    } catch {
      setError('Camera access denied. Check permissions and try again.');
    }
  }, [facingMode]);

  useEffect(() => {
    startCamera();
    return () => {
      stream?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode]);

  const takePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    setIsCapturing(true);
    setTimeout(() => setIsCapturing(false), 150);

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const photo: Photo = { id: Date.now().toString(), dataUrl, date: Date.now() };
    setPhotos((prev) => [photo, ...prev].slice(0, 20));
  };

  const downloadPhoto = (photo: Photo) => {
    const link = document.createElement('a');
    link.download = `photo-${new Date(photo.date).toISOString().slice(0, 19).replace(/:/g, '-')}.jpg`;
    link.href = photo.dataUrl;
    link.click();
  };

  const switchCamera = () => {
    stream?.getTracks().forEach((t) => t.stop());
    setFacingMode((prev) => (prev === 'user' ? 'environment' : 'user'));
  };

  const deletePhoto = (id: string) => setPhotos((prev) => prev.filter((p) => p.id !== id));

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-3">
      <canvas ref={canvasRef} className="hidden" />
      {error && (
        <div className="text-xs text-yellow-400/80 bg-yellow-500/10 rounded-lg px-3 py-2 mb-2 flex items-center gap-2">
          <Camera size={14} />
          {error}
          <button
            onClick={startCamera}
            className="ml-auto px-2 py-0.5 rounded bg-yellow-500/20 hover:bg-yellow-500/30 transition-colors text-[10px]"
          >
            Retry
          </button>
        </div>
      )}
      <div
        className={`flex-1 relative bg-[#0a1420] rounded-xl border border-blue-500/15 overflow-hidden mb-3 ${isCapturing ? 'ring-2 ring-white/50' : ''}`}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
          style={{
            display: stream ? 'block' : 'none',
            transform: facingMode === 'user' ? 'scaleX(-1)' : 'none',
          }}
        />
        {!stream && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <Camera size={48} className="text-blue-400/20" />
            <span className="text-xs text-blue-400/30">Camera off</span>
            <button
              onClick={startCamera}
              className="px-3 py-1 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 text-xs transition-colors"
            >
              Turn on
            </button>
          </div>
        )}
      </div>
      <div className="flex items-center justify-center gap-4 mb-3">
        <button
          onClick={switchCamera}
          className="p-2.5 rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 transition-colors"
          title="Switch camera"
        >
          <SwitchCamera size={18} />
        </button>
        <button
          onClick={takePhoto}
          className="w-14 h-14 rounded-full border-4 border-blue-500/30 flex items-center justify-center hover:border-blue-500/50 transition-colors"
        >
          <div className="w-10 h-10 rounded-full bg-red-500 hover:bg-red-400 transition-colors" />
        </button>
        <button
          onClick={() => stream?.getTracks().forEach((t) => t.stop()) || setStream(null)}
          className="p-2.5 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors"
          title="Stop camera"
        >
          <CircleStop size={18} />
        </button>
      </div>
      {photos.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {photos.map((p) => (
            <div key={p.id} className="flex-shrink-0 relative group">
              <img
                src={p.dataUrl}
                alt=""
                className="w-20 h-14 rounded-lg object-cover border border-blue-500/10"
              />
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-1">
                <button
                  onClick={() => downloadPhoto(p)}
                  className="p-1 rounded bg-blue-500/50 text-white hover:bg-blue-500/70 transition-colors"
                >
                  <Download size={10} />
                </button>
                <button
                  onClick={() => deletePhoto(p.id)}
                  className="p-1 rounded bg-red-500/50 text-white hover:bg-red-500/70 transition-colors"
                >
                  <Trash2 size={10} />
                </button>
              </div>
              <div className="text-[8px] text-blue-400/30 text-center mt-0.5">
                {new Date(p.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
