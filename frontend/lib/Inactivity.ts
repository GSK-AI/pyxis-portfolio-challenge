import { dispatchCustomEvent } from "./utils";
interface CustomWindow extends Window {
  __INACTIVITY__?: InactivityTracker;
}

/**
 * InactivityTracker class monitors user inactivity,
 * and show warning model to refresh session
 */
export default class InactivityTracker {
  private inactivityTimeout: number | undefined;
  private readonly inactivityDuration: number;
  private events: string[];

  /**
   * @constructor
   * Constructs an instance of InactivityTracker.
   * @param inactivityDurationMinutes - The duration of inactivity (in minutes) Default is 30 minutes.
   */
  constructor(inactivityDurationMinutes = 30) {
    // Convert minutes to milliseconds
    this.inactivityDuration = inactivityDurationMinutes * 60 * 1000;
    this.resetInactivityTimeout = this.resetInactivityTimeout.bind(this);
    this.showInactiveModal = this.showInactiveModal.bind(this);
    this.events = ["mousemove", "keydown", "touchstart", "click"];

    // Expose globally
    if (typeof window !== "undefined") {
      (window as CustomWindow).__INACTIVITY__ = this;
    }
  }

  /**
   * Resets the inactivity timeout,
   * scheduling the warning to be shown after the inactivity duration.
   */
  private resetInactivityTimeout(): void {
    if (this.inactivityTimeout !== undefined) {
      clearTimeout(this.inactivityTimeout);
    }
    this.inactivityTimeout = window.setTimeout(
      this.showInactiveModal,
      this.inactivityDuration,
    );
  }

  /**
   * Shows the inactivity warning.
   */
  private showInactiveModal(): void {
    dispatchCustomEvent("inactiveUser");
  }

  /**
   * Initializes the InactivityTracker by setting up event listeners for user activity
   * and starting the inactivity timeout.
   */
  public initialize(): void {
    this.events.forEach((event) =>
      window.addEventListener(event, this.resetInactivityTimeout),
    );
    this.resetInactivityTimeout();
  }

  public destroy() {
    this.events.forEach((event) =>
      window.removeEventListener(event, this.resetInactivityTimeout),
    );

    if (this.inactivityTimeout !== undefined) {
      clearTimeout(this.inactivityTimeout);
    }
  }
}
