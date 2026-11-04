/**
 * Formats integer minor units (paise) into currency string (e.g. ₹1,23,456.78)
 */
export function formatCurrency(minorUnits: number | undefined | null, currency: string = "INR"): string {
  if (minorUnits === undefined || minorUnits === null || isNaN(minorUnits)) {
    return "₹0.00";
  }

  const majorUnits = minorUnits / 100;

  try {
    const formatter = new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
      style: "currency",
      currency: currency || "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return formatter.format(majorUnits);
  } catch (e) {
    return `${currency} ${(majorUnits).toFixed(2)}`;
  }
}

/**
 * Parses user input in Rupees (e.g. "1500.50" or "1,500") into integer minor units (paise)
 */
export function parseToMinorUnits(value: string | number): number {
  if (typeof value === "number") {
    return Math.round(value * 100);
  }
  const cleanStr = value.replace(/,/g, "").trim();
  const num = parseFloat(cleanStr);
  if (isNaN(num)) return 0;
  return Math.round(num * 100);
}

/**
 * Formats a UTC ISO timestamp to localized readable date
 */
export function formatDate(isoString: string | undefined | null): string {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return isoString;
  }
}

/**
 * Formats a UTC ISO timestamp to localized date & time
 */
export function formatDateTime(isoString: string | undefined | null): string {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

