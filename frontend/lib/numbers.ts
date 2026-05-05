export function formatNumber(
  value: number,
  decimals = 0,
  locale = "en-US",
  showZero = false,
): string {
  if (showZero && value === 0) return "0";
  if (!value) return "";

  const fixed = value.toFixed(decimals);
  if (locale) {
    return Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  }

  return fixed;
}

// Format number with M/B suffixes and proper comma formatting
export function formatDisplayNumber(amount: number): string {
  const absoluteAmount = Math.abs(amount);

  if (absoluteAmount >= 1_000_000_000) {
    // Billion
    const billions = amount / 1_000_000_000;
    return `${billions.toFixed(1)}B`;
  } else if (absoluteAmount >= 1_000_000) {
    // Million
    const millions = amount / 1_000_000;
    return `${millions.toFixed(1)}M`;
  } else {
    // Less than million - show with comma formatting
    return formatNumber(amount, 0, "en-US", true);
  }
}

/**
 * Format currency with proper negative sign placement and null/undefined handling
 * @param amount - The amount to format (can be null or undefined)
 * @returns Formatted currency string with £ symbol
 */
export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "N/A";

  const formatted = `£${formatDisplayNumber(Math.abs(amount))}`;
  if (amount < 0) {
    return `-${formatted}`;
  }
  return formatted;
}
