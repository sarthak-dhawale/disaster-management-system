export const advanceEvent = (current, count, amount = 1) => Math.max(0, Math.min(Math.max(0, count - 1), current + amount));
export const playbackDelay = (speed) => 2400 / ([1, 2, 4].includes(Number(speed)) ? Number(speed) : 1);
