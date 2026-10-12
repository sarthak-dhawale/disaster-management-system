import { useEffect, useState } from 'react';
import { subscribe, listeners } from './api';
export function useData(path) {
  const [state, setState] = useState({ loading: true });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const refresh = () => setRevision((v) => v + 1);
    listeners.add(refresh);
    return () => listeners.delete(refresh);
  }, []);
  useEffect(() => {
    if (!path) {
      setState({ loading: false });
      return;
    }
    let active = true;
    setState({ loading: true });
    const subscription = subscribe(path);
    subscription.promise
      .then((data) => {
        if (active) setState({ data, loading: false });
      })
      .catch((error) => {
        if (active) setState({ error, loading: false });
      });
    return () => {
      active = false;
      subscription.release();
    };
  }, [path, revision]);
  return state;
}
export function useDebounced(value, delay = 300) {
  const [result, setResult] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setResult(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return result;
}
export function useRoute() {
  const get = () => location.hash.slice(2).split('?')[0] || 'overview';
  const [route, setRoute] = useState(get);
  useEffect(() => {
    const changed = () => setRoute(get());
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  return route;
}
