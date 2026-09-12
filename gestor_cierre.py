"""
gestor_cierre.py
Modulo de cierre comercial.

Toma los reportes individuales generados en salida/ (Parte 1: secuencial o
concurrente), los clasifica segun su cantidad de "Registros invalidos",
genera un inventario de cierre y una copia de respaldo del consolidado,
dejando constancia de todo en una bitacora persistente.

Uso:  python3 src/gestor_cierre.py
"""

import csv
import os
import re
import shutil
from datetime import datetime

# ---------------------------------------------------------------------------
# Rutas del proyecto (relativas: ejecutar siempre desde la raiz del proyecto)
# ---------------------------------------------------------------------------
SALIDA = "salida"
CIERRE = "cierre_comercial"
APROBADOS = os.path.join(CIERRE, "aprobados")
OBSERVADOS = os.path.join(CIERRE, "observados")
RESPALDOS = os.path.join(CIERRE, "respaldos")
INVENTARIO = os.path.join(CIERRE, "inventario_cierre.csv")
LOGS_DIR = "logs"
LOG = os.path.join(LOGS_DIR, "cierre_comercial.log")
CONSOLIDADO = os.path.join(SALIDA, "consolidado_ventas.txt")

PATRON_REPORTE = re.compile(r"^reporte_ventas_sucursal_(\d+)\.txt$")


# ---------------------------------------------------------------------------
# Bitacora
# ---------------------------------------------------------------------------
def marca_tiempo():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def escribir_log(mensaje):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{marca_tiempo()}] {mensaje}\n")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def preparar_carpetas():
    for carpeta in (APROBADOS, OBSERVADOS, RESPALDOS, LOGS_DIR):
        os.makedirs(carpeta, exist_ok=True)


def destino_unico(carpeta, nombre):
    """Evita sobrescritura: si el nombre existe, agrega sufijo _1, _2, etc."""
    destino = os.path.join(carpeta, nombre)
    if not os.path.exists(destino):
        return destino
    base, ext = os.path.splitext(nombre)
    contador = 1
    while True:
        candidato = os.path.join(carpeta, f"{base}_{contador}{ext}")
        if not os.path.exists(candidato):
            return candidato
        contador += 1


def leer_registros_invalidos(ruta_reporte):
    """Extrae el numero de 'Registros invalidos' desde un reporte individual."""
    with open(ruta_reporte, "r", encoding="utf-8") as f:
        for linea in f:
            minuscula = linea.lower()
            if minuscula.startswith("registros inválidos") or minuscula.startswith("registros invalidos"):
                numero = linea.split(":")[1].strip()
                return int(numero)
    raise ValueError(f"No se encontro la linea 'Registros invalidos' en {ruta_reporte}")


# ---------------------------------------------------------------------------
# Paso principal: clasificar reportes
# ---------------------------------------------------------------------------
def clasificar_reportes():
    filas_inventario = []

    if not os.path.isdir(SALIDA):
        escribir_log(f"ERROR: no existe la carpeta de origen '{SALIDA}'")
        return filas_inventario

    nombres = sorted(os.listdir(SALIDA))

    for nombre in nombres:
        coincidencia = PATRON_REPORTE.match(nombre)
        if not coincidencia:
            continue  # no es un reporte individual (ej: consolidado_ventas.txt)

        origen = os.path.join(SALIDA, nombre)

        # Validar que el origen exista y sea un archivo regular antes de mover.
        if not os.path.isfile(origen):
            escribir_log(f"ERROR: '{origen}' no existe o no es un archivo regular, se omite")
            continue

        try:
            invalidos = leer_registros_invalidos(origen)
        except (ValueError, OSError) as error:
            # Error controlado: se registra y se sigue con el resto de archivos,
            # el programa no termina abruptamente.
            escribir_log(f"ERROR controlado al leer '{origen}': {error}")
            continue

        sucursal = coincidencia.group(1)
        carpeta_destino = APROBADOS if invalidos == 0 else OBSERVADOS
        estado = "aprobado" if invalidos == 0 else "observado"

        destino = destino_unico(carpeta_destino, nombre)

        try:
            info = os.stat(origen)
            shutil.move(origen, destino)
        except OSError as error:
            escribir_log(f"ERROR controlado al mover '{origen}': {error}")
            continue

        escribir_log(
            f"Reporte {nombre} (sucursal {sucursal}, {invalidos} invalidos) "
            f"movido a {destino} [{estado}]"
        )

        filas_inventario.append({
            "nombre_archivo": nombre,
            "tipo_reporte": "reporte_sucursal",
            "sucursal": sucursal,
            "estado": estado,
            "tamano_bytes": info.st_size,
            "fecha_modificacion": datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "ruta_final": destino,
        })

    return filas_inventario


# ---------------------------------------------------------------------------
# Paso: respaldar el consolidado (se COPIA, no se mueve)
# ---------------------------------------------------------------------------
def respaldar_consolidado(filas_inventario):
    if not os.path.isfile(CONSOLIDADO):
        escribir_log(f"ERROR controlado: no se encontro '{CONSOLIDADO}' para respaldar")
        return

    destino = destino_unico(RESPALDOS, os.path.basename(CONSOLIDADO))
    try:
        shutil.copy2(CONSOLIDADO, destino)
    except OSError as error:
        escribir_log(f"ERROR controlado al copiar el consolidado: {error}")
        return

    info = os.stat(destino)
    escribir_log(f"Consolidado {CONSOLIDADO} copiado como respaldo en {destino} (original se mantiene en salida/)")

    filas_inventario.append({
        "nombre_archivo": os.path.basename(destino),
        "tipo_reporte": "consolidado_respaldo",
        "sucursal": "N/A",
        "estado": "respaldado",
        "tamano_bytes": info.st_size,
        "fecha_modificacion": datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "ruta_final": destino,
    })


# ---------------------------------------------------------------------------
# Paso: generar inventario_cierre.csv
# ---------------------------------------------------------------------------
def generar_inventario(filas):
    with open(INVENTARIO, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow([
            "nombre_archivo", "tipo_reporte", "sucursal", "estado",
            "tamano_bytes", "fecha_modificacion", "ruta_final",
        ])
        for fila in filas:
            escritor.writerow([
                fila["nombre_archivo"], fila["tipo_reporte"], fila["sucursal"],
                fila["estado"], fila["tamano_bytes"], fila["fecha_modificacion"],
                fila["ruta_final"],
            ])
    escribir_log(f"Inventario generado en {INVENTARIO} ({len(filas)} filas)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    preparar_carpetas()
    escribir_log("=== Inicio del gestor de cierre comercial ===")

    filas_inventario = clasificar_reportes()
    respaldar_consolidado(filas_inventario)
    generar_inventario(filas_inventario)

    aprobados = sum(1 for f in filas_inventario if f["estado"] == "aprobado")
    observados = sum(1 for f in filas_inventario if f["estado"] == "observado")

    escribir_log(
        f"=== Fin del gestor de cierre comercial "
        f"(aprobados={aprobados}, observados={observados}) ==="
    )

    print(f"Reportes aprobados:  {aprobados}")
    print(f"Reportes observados: {observados}")
    print(f"Inventario generado en: {INVENTARIO}")
    print(f"Bitacora en: {LOG}")


if __name__ == "__main__":
    main()
