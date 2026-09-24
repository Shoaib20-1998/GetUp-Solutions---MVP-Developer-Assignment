import { ApiError } from "./api";

// Turns the error envelope's `details` array into a field -> message map,
// so a form can surface a validation issue right next to the input that
// caused it instead of just showing the top-level message.
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  const map: Record<string, string> = {};
  for (const detail of error.details) {
    map[detail.field] = detail.issue;
  }
  return map;
}

export function topLevelMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something went wrong. Please try again.";
}
