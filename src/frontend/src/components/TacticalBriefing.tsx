import React from 'react';

export default function TacticalBriefing() {
  return (
    <div className="absolute right-4 top-4 z-[100] w-[220px] bg-[#0A0E1A]/90 border border-red-900/40 p-2 rounded shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-right-4 duration-500">
      <div className="flex items-center justify-between border-b border-red-900/40 pb-1 mb-2">
        <span className="text-[10px] font-bold text-red-500 tracking-[0.2em]">MISSION BRIEFING</span>
        <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-ping" />
      </div>
      
      <div className="space-y-2 text-[9px]">
        <div className="flex justify-between">
          <span className="text-gray-500">OPERATION:</span>
          <span className="text-white">SENTINEL-SHIELD</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">ROD:</span>
          <span className="text-white">DEFENSIVE-ONLY</span>
        </div>
        <div className="flex justify-between border-t border-gray-800 pt-1 mt-1">
          <span className="text-gray-500">AUTO-ENGAGE:</span>
          <span className="text-red-400 font-bold">LOCKED</span>
        </div>
        
        <div className="mt-2 p-1.5 bg-red-900/10 border border-red-900/20 rounded">
          <div className="text-[8px] text-red-400 font-bold mb-1">CURRENT ORDERS:</div>
          <div className="text-gray-400 leading-tight">
            Maintain high alert. Monitor ADS-B/AIS discrepancy in North Natuna sector. Report all unidentified military hardware.
          </div>
        </div>
      </div>
      
      <div className="mt-2 h-0.5 w-full bg-red-900/20 overflow-hidden">
        <div className="h-full bg-red-500 animate-[loading_2s_infinite]" style={{ width: '40%' }} />
      </div>
      
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes loading {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(250%); }
        }
      `}} />
    </div>
  );
}
