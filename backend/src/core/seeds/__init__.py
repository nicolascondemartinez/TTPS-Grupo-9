"""Seeds del core. `flask --app main seed-db` los ejecuta en orden."""


def run() -> None:
    from src.core.seeds import seed_catalogos, seed_permisos, seed_usuarios_demo

    seed_permisos.run()
    seed_catalogos.run()
    seed_usuarios_demo.run()