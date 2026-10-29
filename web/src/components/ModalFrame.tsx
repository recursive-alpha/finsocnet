"use client";

import { useEffect, useRef } from "react";

// Escape closes only the topmost open frame, however many are mounted.
const stack: symbol[] = [];

interface ModalFrameProps {
  /** Click outside / the X button. */
  onClose: () => void;
  /** Escape: defaults to `onClose`; a popup with inner views uses it to step back one view first. */
  onEscape?: () => void;
  children: React.ReactNode;
  /** Tailwind max-width class of the dialog. */
  width?: string;
  label?: string;
}

/** Overlay + dialog shell shared by every detail popup: click outside or Escape closes the top one, the page behind does not scroll. */
export function ModalFrame({ onClose, onEscape, children, width = "max-w-5xl", label = "Details" }: ModalFrameProps) {
  const escRef = useRef(onEscape ?? onClose);
  useEffect(() => {
    escRef.current = onEscape ?? onClose;
  });

  useEffect(() => {
    const id = Symbol("modal");
    stack.push(id);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && stack[stack.length - 1] === id) escRef.current();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      stack.splice(stack.indexOf(id), 1);
      if (stack.length === 0) document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/75 p-3 backdrop-blur-xs sm:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className={`relative flex max-h-[92vh] w-full ${width} flex-col overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
