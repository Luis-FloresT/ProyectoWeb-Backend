

def limpiar_texto(texto):
    """Elimina saltos de línea y espacios múltiples de un texto."""
    if not texto:
        return ""
    return " ".join(str(texto).split())
