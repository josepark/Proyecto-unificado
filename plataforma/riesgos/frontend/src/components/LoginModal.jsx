import { useState } from "react";
import { LogIn } from "lucide-react";
import Modal from "./Modal";
import { useAuth } from "../context/AuthContext";

export default function LoginModal({ open, onClose, onSuccess }) {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      setUsername("");
      setPassword("");
      onSuccess?.();
      onClose();
    } catch {
      setError("Usuario o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Iniciar sesión" subtitle="Use su cuenta del Inventario si la plataforma está unificada, o una cuenta propia de riesgos." width="max-w-sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-[12px] font-medium text-base-300">Usuario</label>
          <input
            autoFocus
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg border border-base-700/60 bg-base-850/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500"
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-[12px] font-medium text-base-300">Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-base-700/60 bg-base-850/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500"
            required
          />
        </div>
        {error && <p className="text-[12px] text-[#e0475a]">{error}</p>}
        <p className="text-[11px] text-base-300/70">
          Se prueba primero contra el Inventario y, si no aplica, contra la cuenta propia de
          riesgos — cree esta última con <code className="font-mono-data">python manage.py createsuperuser</code> desde el backend de riesgos si aún no tiene ninguna de las dos.
        </p>
        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-cric-green-600 py-2.5 text-sm font-medium text-base-100 transition-colors hover:bg-cric-green-500 disabled:opacity-60"
        >
          <LogIn className="h-4 w-4" />
          {loading ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </Modal>
  );
}
