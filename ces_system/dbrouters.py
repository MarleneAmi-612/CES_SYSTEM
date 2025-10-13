class CesRouter:
    # Tablas que viven en la BD de simulación
    SIM_TABLES = {"alumnos", "diplomado"}

    def db_for_read(self, model, **hints):
        return "ces_simulacion" if model._meta.db_table in self.SIM_TABLES else "default"

    def db_for_write(self, model, **hints):
        # Nunca escribimos en ces_simulacion
        return "ces_simulacion" if model._meta.db_table in self.SIM_TABLES else "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Nada de migraciones en ces_simulacion
        if db == "ces_simulacion":
            return False
        return None