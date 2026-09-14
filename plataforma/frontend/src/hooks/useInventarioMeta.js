import { useOutletContext } from 'react-router-dom';
import { useApi } from './useApi';
import { inventarioApi } from '../api/inventario';

/** Metadatos del inventario (clases, colores, enums) — se recargan al cambiar de usuario. */
export function useInventarioMeta() {
  const { usuario, autenticado } = useOutletContext() ?? {};
  const { datos, cargando, error, recargar } = useApi(
    () => (autenticado ? inventarioApi.metaInventario() : Promise.resolve(null)),
    [autenticado, usuario],
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
