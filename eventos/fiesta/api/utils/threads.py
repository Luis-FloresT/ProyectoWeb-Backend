import threading

def run_in_background(target, *args, **kwargs):
    """Ejecuta una función en un hilo separado para no bloquear la respuesta."""
    t = threading.Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
