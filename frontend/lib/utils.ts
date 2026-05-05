import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Dispatch custom event
 * @param name {String} - name of the event to dispatch
 * @param data {Object} - data to pass with the event
 */
export function dispatchCustomEvent(name: string, data: unknown = {}) {
  const event: Event = new CustomEvent(name, {
    detail: { data },
  });
  window.dispatchEvent(event);
}
