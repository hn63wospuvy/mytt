// Renders bubbles from the reducer state. vi/en styling; auto-scroll to bottom
// when bubbles change.

import { useEffect, useRef } from "react";
import type { Bubble } from "../transcript";

export function Transcript({ bubbles }: { bubbles: Bubble[] }) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Pin to the bottom of the transcript box itself. Using scrollIntoView here
  // walks up and scrolls every scrollable ancestor — on mobile the outer .panes
  // column also scrolls, so it moved the page instead of the chat frame.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [bubbles]);

  return (
    <div className="transcript" ref={scrollRef}>
      {bubbles.length === 0 ? (
        <p className="transcript-empty">Chưa có hội thoại.</p>
      ) : (
        bubbles.map((b) => {
          const who = b.speaker === "user" ? "Bạn" : "Gia sư";
          const langTag = b.lang === "en" ? " · EN" : " · VI";
          return (
            <div
              key={b.id}
              className={`bubble bubble-${b.speaker} bubble-${b.lang}`}
            >
              <span className="bubble-who">
                {who}
                {langTag}
              </span>
              <span className="bubble-text">{b.text}</span>
            </div>
          );
        })
      )}
    </div>
  );
}
