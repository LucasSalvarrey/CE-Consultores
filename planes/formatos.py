"""Formato de los datos de un plan para mostrarlos en pantalla."""


def pesos(valor):
    """Formato argentino: 12500.5 -> '12.500,50'."""
    texto = f"{valor:,.2f}"  # '12,500.50'
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")