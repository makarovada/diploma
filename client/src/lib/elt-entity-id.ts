/** ELT-сущности в API имеют числовой id. */
export function isNumericEltId(id: string | number | null | undefined): boolean {
  if (id == null) return false;
  return /^\d+$/.test(String(id));
}
