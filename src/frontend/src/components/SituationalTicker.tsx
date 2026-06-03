import { useEffect, useState } from "react";

export default function SituationalTicker() {
  const [summary, setSummary] = useState("SENTINEL-X OPERATIONAL SYSTEMS NOMINAL // GLOBAL THREAT MONITORING ACTIVE");
  const [loading, setLoading] = useState(true);

  const fetchSummary = async () => {
    try {
      const resp = await fetch("/api/v1/analyst/situational-awareness");
      if (resp.ok) {
        const data = await resp.json();
        setSummary(data.summary);
      }
    } catch (err) {
      console.error("Failed to fetch situational awareness:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
    const iv = setInterval(fetchSummary, 60000); // Update every minute
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="w-full bg-[#050B14] border-y border-[#1E3A5F] py-0.5 overflow-hidden whitespace-nowrap relative h-6">
      <div className="flex items-center absolute animate-marquee left-0">
        <span className="text-[10px] font-bold text-[#00D4FF] mx-4">TACTICAL SITREP:</span>
        <span className="text-[10px] text-gray-400 uppercase tracking-wider">{summary}</span>
        <span className="text-[10px] font-bold text-[#00D4FF] mx-8">// SENTINEL ANALYST READY //</span>
        <span className="text-[10px] text-gray-400 uppercase tracking-wider">{summary}</span>
      </div>
      
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes marquee {
          0% { transform: translateX(100%); }
          100% { transform: translateX(-100%); }
        }
        .animate-marquee {
          animation: marquee 90s linear infinite;
        }
      `}} />
    </div>
  );
}
