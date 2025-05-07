# class DatabaseRouter:
#     """
#     Un routeur pour envoyer les modèles User vers la base par défaut,
#     et les modèles AgentUser vers la base super_agent_db.
#     """
#
#     route_app_labels = {'auth', 'contenttypes', 'sessions', 'admin'}
#     agent_models = {'SuperAgent'}
#
#     def db_for_read(self, model, **hints):
#         """Diriger la lecture vers la bonne base de données"""
#         if model._meta.app_label in self.route_app_labels:
#             return 'default'
#         elif model._meta.model_name in self.agent_models:
#             return 'super_agent_db'
#         return None
#
#     def db_for_write(self, model, **hints):
#         """Diriger l'écriture vers la bonne base de données"""
#         if model._meta.app_label in self.route_app_labels:
#             return 'default'
#         elif model._meta.model_name in self.agent_models:
#             return 'super_agent_db'
#         return None
#
#     def allow_relation(self, obj1, obj2, **hints):
#         """Autoriser les relations entre objets des bases séparées"""
#         return True
#
#     def allow_migrate(self, db, app_label, model_name=None, **hints):
#         """Déterminer sur quelle base exécuter les migrations"""
#         if model_name in self.agent_models:
#             return db == 'super_agent_db'
#         return db == 'default'
