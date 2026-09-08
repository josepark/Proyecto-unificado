import { useApi } from './useApi';
import { inventarioApi } from '../api/inventario';

/** Metadatos del inventario (clases, colores, enums) — cache por sesión de componente. */
export function useInventarioMeta() {
  const { datos, cargando, error, recargar } = useApi(
    () => inventarioApi.metaInventario(),
    [],
  );
  return {
    meta: datos,
    clases: datos?.clases ?? [],
    coloresClase: datos?.colores_clase ?? {},
    coloresTipoDc: datos?.datacenter?.colores_tipo ?? {},
    cargando,
    error,
    recargar,
  };
}

export function claseMeta(meta, codigo) {
  return (meta?.clases ?? []).find((c) => c.codigo === codigo);
}
