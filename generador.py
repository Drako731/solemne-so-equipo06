import os
import random
from datetime import datetime, timedelta

# Crear carpeta de entrada si no existe
os.makedirs('entrada', exist_ok=True)

categorias_validas = ['ALIMENTOS', 'TECNOLOGIA', 'HOGAR', 'VESTUARIO']
medios_pago_validos = ['EFECTIVO', 'TARJETA', 'TRANSFERENCIA']
fecha_base = datetime(2026, 9, 2)

for i in range(1, 21): # Generar 20 archivos
    nombre_archivo = f'entrada/ventas_sucursal_{i:03d}.csv'

    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        # 1. Escribir cabecera obligatoria
        f.write("id_venta;fecha;codigo_producto;categoria;cantidad;precio_unitario;medio_pago\n")

        # 2. Garantizar 2 categorías distintas y 2 medios de pago distintos
        cat1, cat2 = random.sample(categorias_validas, 2)
        pago1, pago2 = random.sample(medios_pago_validos, 2)

        # 3. Garantizar al menos 1 producto repetido
        prod_repetido = f"P{random.randint(1000, 2000)}"

        registros = []

        # Agregar los 2 registros con el producto repetido (usando diferentes categorías/pagos para cumplir mínimos)
        registros.append(f"V001;{fecha_base.strftime('%Y-%m-%d')};{prod_repetido};{cat1};{random.randint(1, 5)};{random.randint(1000, 50000)};{pago1}\n")
        registros.append(f"V002;{fecha_base.strftime('%Y-%m-%d')};{prod_repetido};{cat2};{random.randint(1, 5)};{random.randint(1000, 50000)};{pago2}\n")

        # 4. Generar el resto de los registros válidos hasta llegar a 10
        for j in range(3, 11):
            fecha_venta = (fecha_base + timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d')
            prod = f"P{random.randint(3000, 9999)}"
            cat = random.choice(categorias_validas)
            cant = random.randint(1, 10)
            precio = random.randint(1500, 200000)
            pago = random.choice(medios_pago_validos)

            registros.append(f"V{j:03d};{fecha_venta};{prod};{cat};{cant};{precio};{pago}\n")

        # 5. Generar al menos 1 registro inválido (violando varias reglas: cantidad negativa y categoría inválida)
        id_invalido = "V011"
        fecha_invalida = "02-09-2026" # Formato incorrecto, debería ser AAAA-MM-DD
        cat_invalida = "JUGUETES" # No está en las 4 permitidas
        cant_invalida = "-5" # Debe ser mayor a 0

        registros.append(f"{id_invalido};{fecha_invalida};P9999;{cat_invalida};{cant_invalida};1000;CHEQUE\n")

        # Escribir todos los registros en el archivo
        f.writelines(registros)

print("¡20 archivos generados con éxito en la carpeta 'entrada/'!")