import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState<string>("checking...");

  useEffect(() => {
    fetch("/api/health", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setStatus(d.status ?? "unknown"))
      .catch((e) => setStatus("error: " + String(e)));
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <h1>Moments</h1>
      <p>Backend health: {status}</p>
    </div>
  );
}