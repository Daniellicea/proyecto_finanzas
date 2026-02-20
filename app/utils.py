def generar_plan(deudas):
    # Método Avalancha: Ordena por tasa de interés de mayor a menor
    deudas_ordenadas = sorted(deudas, key=lambda x: x.tasa, reverse=True)
    
    total_deuda = sum(d.monto for d in deudas)
    pago_minimo_total = sum(d.minimo for d in deudas)
    
    return {
        'lista': deudas_ordenadas,
        'total': total_deuda,
        'minimo_total': pago_minimo_total,
        'estrategia': 'Método Avalancha (Prioridad Intereses Altos)'
    }