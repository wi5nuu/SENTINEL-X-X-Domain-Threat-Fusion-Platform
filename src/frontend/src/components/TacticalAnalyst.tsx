import { useState, useRef, useEffect } from "react";

type Message = {
  role: "user" | "analyst";
  content: string;
  timestamp: string;
};

export default function TacticalAnalyst() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "analyst", content: "Sentinel Analyst online. Tactical context loaded. How can I assist?", timestamp: new Date().toLocaleTimeString() }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: "user", content: input, timestamp: new Date().toLocaleTimeString() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const resp = await fetch("/api/v1/analyst/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setMessages(prev => [...prev, { role: "analyst", content: data.response, timestamp: new Date().toLocaleTimeString() }]);
      } else {
        setMessages(prev => [...prev, { role: "analyst", content: "Error: Communications link degraded.", timestamp: new Date().toLocaleTimeString() }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "analyst", content: "Error: Connection timeout.", timestamp: new Date().toLocaleTimeString() }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {/* Trigger Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-12 right-6 z-[100] w-12 h-12 rounded-full border border-[#00D4FF] bg-[#0A0E1A] flex items-center justify-center shadow-lg hover:scale-110 transition-transform"
      >
        <span className="text-[#00D4FF] text-lg">AI</span>
      </button>

      {/* Sidebar Drawer */}
      <div className={`fixed top-0 right-0 h-full w-[320px] bg-[#0A0E1A] border-l border-[#1E3A5F] z-[1000] transition-transform duration-300 transform ${isOpen ? "translate-x-0" : "translate-x-full"} flex flex-col shadow-2xl`}>
        <div className="p-3 border-b border-[#1E3A5F] flex justify-between items-center bg-[#050B14]">
          <span className="text-xs font-bold text-[#00D4FF] tracking-widest">SENTINEL-ANALYST</span>
          <button onClick={() => setIsOpen(false)} className="text-gray-500 hover:text-white">✕</button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
              <div className={`max-w-[85%] p-2 rounded text-[11px] leading-relaxed ${
                m.role === "user" 
                ? "bg-[#1E3A5F] text-white border border-[#00D4FF]/20" 
                : "bg-[#050B14] text-[#94A3B8] border border-[#1E3A5F]"
              }`}>
                {m.content}
              </div>
              <span className="text-[8px] text-gray-600 mt-1">{m.timestamp}</span>
            </div>
          ))}
          {isTyping && (
            <div className="text-[9px] text-[#00D4FF] animate-pulse">Analyst is processing context...</div>
          )}
        </div>

        <div className="p-3 border-t border-[#1E3A5F] bg-[#050B14]">
          <div className="flex gap-2">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask analyst..."
              className="flex-1 bg-[#0A0E1A] border border-[#1E3A5F] rounded px-2 py-1 text-xs text-white outline-none focus:border-[#00D4FF]"
            />
            <button onClick={handleSend} className="text-[#00D4FF] text-xs font-bold px-2">SEND</button>
          </div>
        </div>
      </div>
    </>
  );
}
