"""Enruta la app rbac a la base de datos dedicada (alias ``rbac``)."""


class RbacRouter:
    app_label = 'rbac'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return 'rbac'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return 'rbac'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == self.app_label or obj2._meta.app_label == self.app_label:
            return (
                obj1._meta.app_label == self.app_label
                and obj2._meta.app_label == self.app_label
            )
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.app_label:
            return db == 'rbac'
        if db == 'rbac':
            return False
        return None
