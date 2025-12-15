// @ts-check

/**
 * @param {any} value
 * @returns {Promise<string>}
 */
export async function sha256Json(value) {
  const str = JSON.stringify(value, Object.keys(value).sort());
  const bytes = new TextEncoder().encode(str);
  const hashBuffer = await crypto.subtle.digest("SHA-256", bytes);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

