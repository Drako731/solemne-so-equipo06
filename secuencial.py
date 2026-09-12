import os
import glob
import time
from datetime import datetime

def validar_campos(linea, ids_vistos):
    campos = linea.strip().split(';')
    if len(campos) != 7: return False, "Número incorrecto de campos"
    
    id_venta, fecha, cod, cat, cant, precio, pago = campos
    
    if not id_venta: return False, "ID de venta vacío"
    if id_venta in ids_vistos: return False, "ID de venta duplicado"
    
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return False, "Formato de fecha incorrecto"
        
    if not cod: return False, "Código de producto vacío"
    if cat not in ["ALIMENTOS", "TECNOLOGIA", "HOGAR", "VESTUARIO"]: return False, "Categoría inválida"
    
    try:
        cant = int(cant)
        if cant <= 0: return False, "Cantidad debe ser mayor a 0"
    except ValueError: return False, "Cantidad no es un entero"
    
    try:
        precio = int(precio)
        if precio <= 0: return False, "Precio debe ser mayor a 0"
    except ValueError: return False, "Precio no es un entero"
    
    if pago not in ["EFECTIVO", "TARJETA", "TRANSFERENCIA"]: return False, "Medio de pago inválido"
    
    ids_vistos.add(id_venta)
    return True, (id_venta, fecha, cod, cat, cant, precio, pago)

def ejecutar_secuencial():
    os.makedirs('salida', exist_ok=True)
    os.makedirs('errores', exist_ok=True)
    
    # Limpiar archivo de errores previo
    ruta_errores = os.path.join('errores', 'registros_invalidos.txt')
    open(ruta_errores, 'w', encoding='utf-8').close()

    archivos = glob.glob(os.path.join('entrada', '*.csv'))
    
    g_archivos = 0
    g_leidos = 0
    g_validos = 0
    g_invalidos = 0
    g_unidades = 0
    g_monto = 0
    g_cat_monto = {}
    g_pago_uso = {}
    g_prod_unidades = {}

    inicio_tiempo = time.time()

    for archivo in archivos:
        ids_vistos = set()
        l_leidos = l_validos = l_invalidos = l_unidades = l_monto = 0
        l_cat_monto, l_pago_uso, l_prod_unidades = {}, {}, {}
        
        sucursal = os.path.basename(archivo).replace('ventas_sucursal_', '').replace('.csv', '')
        
        with open(archivo, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            
        if not lineas: continue
        
        g_archivos += 1
        
        with open(ruta_errores, 'a', encoding='utf-8') as f_err:
            for num_linea, linea in enumerate(lineas[1:], start=2): # Ignorar cabecera
                if not linea.strip(): continue
                l_leidos += 1
                
                es_valido, resultado = validar_campos(linea, ids_vistos)
                
                if not es_valido:
                    l_invalidos += 1
                    f_err.write(f"Archivo: {archivo} | Linea: {num_linea} | Motivo: {resultado} | Contenido: {linea.strip()}\n")
                else:
                    l_validos += 1
                    _, _, cod, cat, cant, precio, pago = resultado
                    monto_venta = cant * precio
                    
                    # Acumuladores locales
                    l_unidades += cant
                    l_monto += monto_venta
                    l_cat_monto[cat] = l_cat_monto.get(cat, 0) + monto_venta
                    l_pago_uso[pago] = l_pago_uso.get(pago, 0) + 1
                    l_prod_unidades[cod] = l_prod_unidades.get(cod, 0) + cant
                    
                    # Acumuladores globales
                    g_unidades += cant
                    g_monto += monto_venta
                    g_cat_monto[cat] = g_cat_monto.get(cat, 0) + monto_venta
                    g_pago_uso[pago] = g_pago_uso.get(pago, 0) + 1
                    g_prod_unidades[cod] = g_prod_unidades.get(cod, 0) + cant
        
        g_leidos += l_leidos
        g_validos += l_validos
        g_invalidos += l_invalidos

        # Generar reporte individual
        cat_top = max(l_cat_monto, key=l_cat_monto.get) if l_cat_monto else "N/A"
        pago_top = max(l_pago_uso, key=l_pago_uso.get) if l_pago_uso else "N/A"
        prod_top = max(l_prod_unidades, key=l_prod_unidades.get) if l_prod_unidades else "N/A"
        
        repo_path = os.path.join('salida', f'reporte_ventas_sucursal_{sucursal}.txt')
        with open(repo_path, 'w', encoding='utf-8') as f_rep:
            f_rep.write("REPORTE DE VENTAS POR SUCURSAL\n")
            f_rep.write(f"Archivo procesado: ventas_sucursal_{sucursal}.csv\n")
            f_rep.write(f"Sucursal: {sucursal}\n")
            f_rep.write(f"Registros leídos: {l_leidos}\n")
            f_rep.write(f"Registros válidos: {l_validos}\n")
            f_rep.write(f"Registros inválidos: {l_invalidos}\n")
            f_rep.write(f"Unidades vendidas: {l_unidades}\n")
            f_rep.write(f"Monto total vendido: ${l_monto:,}\n")
            f_rep.write(f"Categoría con mayor venta: {cat_top}\n")
            f_rep.write(f"Medio de pago más utilizado: {pago_top}\n")
            f_rep.write(f"Producto más vendido: {prod_top}\n")

    tiempo_total = time.time() - inicio_tiempo

    # Generar reporte consolidado
    g_cat_top = max(g_cat_monto, key=g_cat_monto.get) if g_cat_monto else "N/A"
    g_pago_top = max(g_pago_uso, key=g_pago_uso.get) if g_pago_uso else "N/A"
    
    with open(os.path.join('salida', 'consolidado_ventas.txt'), 'w', encoding='utf-8') as f_cons:
        f_cons.write("REPORTE CONSOLIDADO DE VENTAS\n")
        f_cons.write("Versión ejecutada: secuencial\n")
        f_cons.write(f"Archivos procesados: {g_archivos}\n")
        f_cons.write(f"Registros leídos: {g_leidos}\n")
        f_cons.write(f"Registros válidos: {g_validos}\n")
        f_cons.write(f"Registros inválidos: {g_invalidos}\n")
        f_cons.write(f"Unidades vendidas: {g_unidades}\n")
        f_cons.write(f"Monto total vendido: ${g_monto:,}\n")
        f_cons.write(f"Categoría con mayor monto acumulado: {g_cat_top}\n")
        f_cons.write(f"Medio de pago más utilizado: {g_pago_top}\n")
        f_cons.write(f"Tiempo total de ejecución: {tiempo_total:.4f} segundos\n")
        f_cons.write("Cantidad de trabajadores: 1\n")

if __name__ == "__main__":
    ejecutar_secuencial()
