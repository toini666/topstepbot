import { formatInTimeZone } from 'date-fns-tz';

let _userTimezone = 'Europe/Brussels';

export function setUserTimezone(tz: string) {
  _userTimezone = tz;
}

export function getUserTimezone(): string {
  return _userTimezone;
}

/**
 * Format a UTC timestamp in the user's configured timezone.
 * Drop-in replacement for format(new Date(timestamp), pattern).
 */
export function formatInUserTz(timestamp: string | Date, pattern: string): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  return formatInTimeZone(date, _userTimezone, pattern);
}

/**
 * Get "today" as a yyyy-MM-dd string in the user's configured timezone.
 */
export function todayStringInUserTz(): string {
  return formatInTimeZone(new Date(), _userTimezone, 'yyyy-MM-dd');
}

/**
 * Get start of today (midnight) in the user's timezone, as a UTC ISO string.
 * Useful for API queries that need a UTC timestamp for "start of today".
 */
export function todayMidnightUtcIso(): string {
  const todayStr = formatInTimeZone(new Date(), _userTimezone, 'yyyy-MM-dd');
  // Parse as midnight in the user's timezone by constructing an ISO string
  // and letting the Date constructor handle it
  const midnightLocal = formatInTimeZone(
    new Date(todayStr + 'T00:00:00'),
    _userTimezone,
    "yyyy-MM-dd'T'HH:mm:ssXXX"
  );
  return new Date(midnightLocal).toISOString();
}
