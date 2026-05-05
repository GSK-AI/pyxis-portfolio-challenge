import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cn, dispatchCustomEvent } from "./utils";

// Mock window.dispatchEvent for testing
const mockDispatchEvent = vi.fn();
Object.defineProperty(window, "dispatchEvent", {
  value: mockDispatchEvent,
  writable: true,
});

describe("utils.ts", () => {
  describe("cn function", () => {
    it("should be defined", () => {
      expect(cn).toBeDefined();
      expect(typeof cn).toBe("function");
    });

    it("should merge basic class names", () => {
      const result = cn("class1", "class2");
      expect(result).toBe("class1 class2");
    });

    it("should handle conditional classes", () => {
      const result = cn("base", true && "conditional", false && "hidden");
      expect(result).toBe("base conditional");
    });

    it("should handle objects with boolean values", () => {
      const result = cn({
        active: true,
        inactive: false,
        visible: true,
      });
      expect(result).toBe("active visible");
    });

    it("should handle arrays of classes", () => {
      const result = cn(["class1", "class2"], ["class3"]);
      expect(result).toBe("class1 class2 class3");
    });

    it("should handle mixed input types", () => {
      const result = cn(
        "base",
        ["array-class"],
        { "object-class": true, hidden: false },
        true && "conditional",
      );
      expect(result).toBe("base array-class object-class conditional");
    });

    it("should handle empty inputs", () => {
      const result = cn();
      expect(result).toBe("");
    });

    it("should handle null and undefined inputs", () => {
      const result = cn(null, undefined, "valid-class");
      expect(result).toBe("valid-class");
    });

    it("should merge conflicting Tailwind classes (tailwind-merge functionality)", () => {
      // tailwind-merge should handle conflicting utility classes
      const result = cn("px-2 px-4"); // Should keep only px-4
      expect(result).toBe("px-4");
    });

    it("should handle complex Tailwind class conflicts", () => {
      const result = cn("bg-red-500 bg-blue-500 text-sm text-lg");
      expect(result).toBe("bg-blue-500 text-lg");
    });

    it("should preserve non-conflicting classes", () => {
      const result = cn("px-4 py-2 bg-blue-500 text-white hover:bg-blue-600");
      expect(result).toBe("px-4 py-2 bg-blue-500 text-white hover:bg-blue-600");
    });

    it("should handle responsive and state variants", () => {
      const result = cn("md:px-4 lg:px-6 hover:px-8");
      expect(result).toBe("md:px-4 lg:px-6 hover:px-8");
    });

    it("should work with complex conditional logic", () => {
      const isActive = true;
      const isDisabled = false;
      const size = "large";

      const result = cn(
        "base-class",
        isActive && "active",
        isDisabled && "disabled",
        size === "large" && "text-lg",
        {
          "font-bold": isActive,
          "opacity-50": isDisabled,
        },
      );
      expect(result).toBe("base-class active text-lg font-bold");
    });
  });

  describe("dispatchCustomEvent function", () => {
    beforeEach(() => {
      mockDispatchEvent.mockClear();
    });

    afterEach(() => {
      vi.clearAllMocks();
    });

    it("should be defined", () => {
      expect(dispatchCustomEvent).toBeDefined();
      expect(typeof dispatchCustomEvent).toBe("function");
    });

    it("should dispatch a custom event with default data", () => {
      const eventName = "test-event";

      dispatchCustomEvent(eventName);

      expect(mockDispatchEvent).toHaveBeenCalledTimes(1);
      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent).toBeInstanceOf(CustomEvent);
      expect(calledEvent.type).toBe(eventName);
      expect(calledEvent.detail).toEqual({ data: {} });
    });

    it("should dispatch a custom event with provided data", () => {
      const eventName = "custom-event";
      const eventData = { message: "Hello World", count: 42 };

      dispatchCustomEvent(eventName, eventData);

      expect(mockDispatchEvent).toHaveBeenCalledTimes(1);
      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent).toBeInstanceOf(CustomEvent);
      expect(calledEvent.type).toBe(eventName);
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle string data", () => {
      const eventName = "string-event";
      const eventData = "test string";

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle number data", () => {
      const eventName = "number-event";
      const eventData = 123;

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle boolean data", () => {
      const eventName = "boolean-event";
      const eventData = true;

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle null data", () => {
      const eventName = "null-event";
      const eventData = null;

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle undefined data explicitly (uses default value)", () => {
      const eventName = "undefined-event";
      const eventData = undefined;

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      // In JavaScript, passing undefined explicitly triggers the default parameter value
      expect(calledEvent.detail).toEqual({ data: {} });
    });

    it("should use default empty object when no data parameter provided", () => {
      const eventName = "no-data-event";

      // Call without second parameter
      dispatchCustomEvent(eventName);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: {} });
    });

    it("should handle array data", () => {
      const eventName = "array-event";
      const eventData = [1, 2, 3, "test"];

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle complex object data", () => {
      const eventName = "complex-event";
      const eventData = {
        user: { id: 1, name: "John" },
        settings: { theme: "dark", notifications: true },
        metadata: { timestamp: Date.now(), version: "1.0.0" },
      };

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });

    it("should handle event names with special characters", () => {
      const eventName = "test-event_with.special@chars";

      dispatchCustomEvent(eventName);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.type).toBe(eventName);
    });

    it("should create a new CustomEvent instance each time", () => {
      dispatchCustomEvent("event1");
      dispatchCustomEvent("event2");

      expect(mockDispatchEvent).toHaveBeenCalledTimes(2);
      const event1 = mockDispatchEvent.mock.calls[0][0];
      const event2 = mockDispatchEvent.mock.calls[1][0];

      expect(event1).not.toBe(event2);
      expect(event1.type).toBe("event1");
      expect(event2.type).toBe("event2");
    });

    it("should maintain data integrity across multiple dispatches", () => {
      const data1 = { id: 1 };
      const data2 = { id: 2 };

      dispatchCustomEvent("event1", data1);
      dispatchCustomEvent("event2", data2);

      const event1 = mockDispatchEvent.mock.calls[0][0];
      const event2 = mockDispatchEvent.mock.calls[1][0];

      expect(event1.detail.data).toEqual(data1);
      expect(event2.detail.data).toEqual(data2);
      expect(event1.detail.data).not.toEqual(event2.detail.data);
    });

    it("should work with empty string event name", () => {
      const eventName = "";

      dispatchCustomEvent(eventName);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.type).toBe(eventName);
    });

    it("should handle function data (serializable)", () => {
      const eventName = "function-event";
      const eventData = () => "test function";

      dispatchCustomEvent(eventName, eventData);

      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail).toEqual({ data: eventData });
    });
  });

  describe("Integration tests", () => {
    it("should work together in a realistic scenario", () => {
      // Using cn to create class names for UI elements
      const buttonClasses = cn(
        "px-4 py-2 rounded",
        "bg-blue-500 text-white",
        "hover:bg-blue-600",
        { "opacity-50": false, "cursor-pointer": true },
      );

      expect(buttonClasses).toBe(
        "px-4 py-2 rounded bg-blue-500 text-white hover:bg-blue-600 cursor-pointer",
      );

      // Dispatching an event with the button interaction
      const eventData = {
        action: "button-click",
        element: "submit-button",
        classes: buttonClasses,
      };

      dispatchCustomEvent("ui-interaction", eventData);

      expect(mockDispatchEvent).toHaveBeenCalledTimes(1);
      const calledEvent = mockDispatchEvent.mock.calls[0][0];
      expect(calledEvent.detail.data).toEqual(eventData);
    });
  });
});
