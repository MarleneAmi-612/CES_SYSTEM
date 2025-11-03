# ces_system/routers.py

class SimulationRouter:
    """
    Mantén 'default' (ces_db) como base real de Django.
    Protege 'ces' (ces_simulacion): sin migraciones y sin escrituras accidentales.
    No forzamos lecturas a 'ces'; usar .using('ces') solo cuando lo pidas explícitamente.
    """
    def db_for_read(self, model, **hints):
        # No desviamos lecturas; Django usará 'default' salvo que llames .using('ces')
        return None

    def db_for_write(self, model, **hints):
        # Todas las escrituras a 'default' (ces_db)
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Permite relaciones entre objetos (no restringimos por DB)
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Nunca migres contra 'ces' (simulación)
        if db == 'ces':
            return False
        return True
