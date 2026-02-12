const TELEMETRY_ENABLED = import.meta.env.DEV && import.meta.env.VITE_TELEMETRY === '1';
const TELEMETRY_ENDPOINT = '/api/telemetry/log';

type TelemetryLevel = 'log' | 'warn' | 'error' | 'info' | 'debug';

const safeStringify = (value: unknown) => {
  try {
    return JSON.stringify(value);
  } catch (error) {
    return String(value);
  }
};

const buildPayload = (level: TelemetryLevel, args: unknown[], sessionId: string) => {
  const [first, ...rest] = args;
  return {
    level,
    message: typeof first === 'string' ? first : safeStringify(first),
    args: rest.map(item => {
      try {
        return JSON.parse(safeStringify(item));
      } catch (error) {
        return String(item);
      }
    }),
    timestamp: new Date().toISOString(),
    source: 'client',
    context: {
      path: window.location.pathname,
      userAgent: navigator.userAgent,
      sessionId
    }
  };
};

export const initTelemetry = () => {
  if (!TELEMETRY_ENABLED) return;

  const sessionId = crypto.randomUUID();
  const original = {
    log: console.log,
    warn: console.warn,
    error: console.error,
    info: console.info,
    debug: console.debug
  };

  const wrap = (level: TelemetryLevel) => (...args: unknown[]) => {
    original[level](...args);
    fetch(TELEMETRY_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPayload(level, args, sessionId))
    }).catch(() => {});
  };

  console.log = wrap('log');
  console.warn = wrap('warn');
  console.error = wrap('error');
  console.info = wrap('info');
  console.debug = wrap('debug');
};
