import os
import time
import threading
from queue import Queue
from collections import Counter

CATEGORIAS_VALIDAS = {"ALIMENTOS", "TECNOLOGIA", "HOGAR", "VESTUARIO"}
MEDIOS_PAGO_VALIDOS = {"EFECTIVO", "TARJETA", "TRANSFERENCIA"}

# Estructuras de Sincronización y Globales
lock_global = threading.Lock()
lock_archivo_errores = threading.Lock()

total_archivos = 0
total_leidos = 0
total_validos = 0
total_invalidos = 0
total_unidades = 0
monto_total = 0

cat_global = Counter()
pago_global = Counter()
prod_global = Counter()

cola_archivos = Queue()

def validar_registro(linea, ids_vistos):
    partes = linea.strip().split(";")
    if len(partes) != 7:
        return False, "Cantidad de campos incorrecta"

    id_venta, fecha, cod_prod, cat, cant, precio, pago = partes

    if not id_venta or id_venta in ids_vistos:
        return False, "ID de venta vacío o duplicado"
    if len(fecha.split("-")) != 3:
        return False, "Formato de fecha inválido"
    if not cod_prod:
        return False, "Código de producto vacío"
    if cat not in CATEGORIAS_VALIDAS:
        return False, f"Categoría inválida ({cat})"
    try:
        if int(cant) <= 0:
            return False, "Cantidad debe ser entero mayor a 0"
        if int(precio) <= 0:
            return False, "Precio unitario debe ser mayor a 0"
    except ValueError:
        return False, "Cantidad o Precio no son enteros"
    if pago not in MEDIOS_PAGO_VALIDOS:
        return False, f"Medio de pago inválido ({pago})"

    ids_vistos.add(id_venta)
    return True, "OK"

def trabajador():
    global total_leidos, total_validos, total_invalidos, total_unidades, monto_total

    while True:
        arch = cola_archivos.get()
        if arch is None:
            break

        ruta = os.path.join("entrada", arch)
        ids_vistos = set()

        c_leidos = 0
        c_validos = 0
        c_invalidos = 0
        c_unidades = 0
        c_monto = 0

        cat_local = Counter()
        pago_local = Counter()
        prod_local = Counter()

        with open(ruta, "r", encoding="utf-8") as f:
            header = f.readline()
            for num_linea, linea in enumerate(f, start=2):
                if not linea.strip():
                    continue
                c_leidos += 1
                es_valido, motivo = validar_registro(linea, ids_vistos)

                if es_valido:
                    c_validos += 1
                    _, _, cod_prod, cat, cant, precio, pago = linea.strip().split(";")
                    cant, precio = int(cant), int(precio)

                    subtotal = cant * precio
                    c_unidades += cant
                    c_monto += subtotal

                    cat_local[cat] += subtotal
                    pago_local[pago] += 1
                    prod_local[cod_prod] += cant
                else:
                    c_invalidos += 1
                    # Sección Crítica: Escritura concurrente de errores protegida
                    with lock_archivo_errores:
                        with open("errores/registros_invalidos.txt", "a", encoding="utf-8") as f_err:
                            f_err.write(f"{arch};{num_linea};{motivo};{linea.strip()}\n")

        # Reporte Individual por sucursal
        num_sucursal = arch.replace("ventas_sucursal_", "").replace(".csv", "")
        top_cat = cat_local.most_common(1)[0][0] if cat_local else "N/A"
        top_pago = pago_local.most_common(1)[0][0] if pago_local else "N/A"
        top_prod = prod_local.most_common(1)[0][0] if prod_local else "N/A"

        rep_ind_path = f"salida/reporte_ventas_sucursal_{num_sucursal}.txt"
        with open(rep_ind_path, "w", encoding="utf-8") as f_rep:
            f_rep.write("REPORTE DE VENTAS POR SUCURSAL\n\n")
            f_rep.write(f"Archivo procesado: {arch}\n")
            f_rep.write(f"Sucursal: {num_sucursal}\n")
            f_rep.write(f"Registros leídos: {c_leidos}\n")
            f_rep.write(f"Registros válidos: {c_validos}\n")
            f_rep.write(f"Registros inválidos: {c_invalidos}\n")
            f_rep.write(f"Unidades vendidas: {c_unidades}\n")
            f_rep.write(f"Monto total vendido: ${c_monto:,}\n")
            f_rep.write(f"Categoría con mayor venta: {top_cat}\n")
            f_rep.write(f"Medio de pago más utilizado: {top_pago}\n")
            f_rep.write(f"Producto más vendido: {top_prod}\n")

        # Sección Crítica: Actualización de globales acumulados
        with lock_global:
            total_leidos += c_leidos
            total_validos += c_validos
            total_invalidos += c_invalidos
            total_unidades += c_unidades
            monto_total += c_monto
            cat_global.update(cat_local)
            pago_global.update(pago_local)
            prod_global.update(prod_local)

        cola_archivos.task_done()

def procesar_concurrente(num_workers=4):
    global total_archivos
    inicio_tiempo = time.time()

    with open("errores/registros_invalidos.txt", "w", encoding="utf-8") as f_err:
        f_err.write("Archivo;numero_linea;motivo;contenido_original\n")

    archivos = [f for f in os.listdir("entrada") if f.endswith(".csv")]
    total_archivos = len(archivos)

    for arch in sorted(archivos):
        cola_archivos.put(arch)

    hilos = []
    for _ in range(num_workers):
        t = threading.Thread(target=trabajador)
        t.start()
        hilos.append(t)

    cola_archivos.join()

    # Enviar señal de parada a trabajadores
    for _ in range(num_workers):
        cola_archivos.put(None)
    for t in hilos:
        t.join()

    tiempo_total = time.time() - inicio_tiempo

    # Reporte Consolidado
    g_cat = cat_global.most_common(1)[0][0] if cat_global else "N/A"
    g_pago = pago_global.most_common(1)[0][0] if pago_global else "N/A"

    with open("salida/consolidado_ventas.txt", "w", encoding="utf-8") as f_cons:
        f_cons.write("REPORTE CONSOLIDADO DE VENTAS\n\n")
        f_cons.write("Versión ejecutada: concurrente\n")
        f_cons.write(f"Archivos procesados: {total_archivos}\n")
        f_cons.write(f"Registros leídos: {total_leidos}\n")
        f_cons.write(f"Registros válidos: {total_validos}\n")
        f_cons.write(f"Registros inválidos: {total_invalidos}\n")
        f_cons.write(f"Unidades vendidas: {total_unidades}\n")
        f_cons.write(f"Monto total vendido: ${monto_total:,}\n")
        f_cons.write(f"Categoría con mayor monto acumulado: {g_cat}\n")
        f_cons.write(f"Medio de pago más utilizado: {g_pago}\n")
        f_cons.write(f"Tiempo total de ejecución: {tiempo_total:.4f} segundos\n")
        f_cons.write(f"Cantidad de trabajadores: {num_workers}\n")

if __name__ == "__main__":
    procesar_concurrente(num_workers=4)