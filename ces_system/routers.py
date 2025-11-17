class SimulationRouter:
    """
    Envía ProgramSim a la base 'ces' (ces_simulacion)
    Todo lo demás queda en 'default'
    """

    app_labels_sim = {"administracion"}   # apps que contienen ProgramSim
    model_names_sim = {"programsim"}      # modelos que van a la simulación

    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.model_names_sim:
            return "ces"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.model_names_sim:
            return "ces"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # ProgramSim NO migra
        if model_name in self.model_names_sim:
            return False
        return None
