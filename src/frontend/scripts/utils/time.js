// @ts-check

const WEEKDAY_NAMES = [
  "星期日",
  "星期一",
  "星期二",
  "星期三",
  "星期四",
  "星期五",
  "星期六",
];

/**
 * @param {number} timestampSec
 */
export function formatChatTimestamp(timestampSec) {
  const date = new Date(timestampSec * 1000);
  const now = new Date();

  const isToday = date.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const weekAgo = new Date(now);
  weekAgo.setDate(weekAgo.getDate() - 7);
  const isThisWeek = date > weekAgo;

  const isThisYear = date.getFullYear() === now.getFullYear();

  const hh = date.getHours().toString().padStart(2, "0");
  const mm = date.getMinutes().toString().padStart(2, "0");
  const timeStr = `${hh}:${mm}`;

  if (isToday) return timeStr;
  if (isYesterday) return `昨天 ${timeStr}`;
  if (isThisWeek) return `${WEEKDAY_NAMES[date.getDay()]} ${timeStr}`;

  const month = date.getMonth() + 1;
  const day = date.getDate().toString().padStart(2, "0");
  if (isThisYear) return `${month}月${day}日 ${timeStr}`;

  const year = date.getFullYear();
  return `${year}年${month}月${day}日 ${timeStr}`;
}

/**
 * Session list time: same rules but no HH:mm except for today.
 * @param {number} timestampSec
 */
export function formatSessionTimestamp(timestampSec) {
  const date = new Date(timestampSec * 1000);
  const now = new Date();

  const isToday = date.toDateString() === now.toDateString();
  if (isToday) {
    const hh = date.getHours().toString().padStart(2, "0");
    const mm = date.getMinutes().toString().padStart(2, "0");
    return `${hh}:${mm}`;
  }

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const weekAgo = new Date(now);
  weekAgo.setDate(weekAgo.getDate() - 7);
  const isThisWeek = date > weekAgo;

  const isThisYear = date.getFullYear() === now.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate().toString().padStart(2, "0");

  if (isYesterday) return "昨天";
  if (isThisWeek) return WEEKDAY_NAMES[date.getDay()];
  if (isThisYear) return `${month}月${day}日`;

  const year = date.getFullYear();
  return `${year}年${month}月${day}日`;
}

