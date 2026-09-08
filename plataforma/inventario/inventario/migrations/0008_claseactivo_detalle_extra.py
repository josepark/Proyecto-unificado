# Generated manually — catálogo dinámico de clases de activo

from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


CLASES_INICIALES = [
    ("INFRA", "Infraestructura de red", "RED", "#1f6b52", 1, "infraestructura"),
    ("SIST", "Sistema de informacion", "SIS", "#c9a94e", 2, "sistema"),
    ("EQUI", "Equipo de computo", "PC", "#28407a", 3, "equipo"),
]


def poblar_clases(apps, schema_editor):
    ClaseActivo = apps.get_model("inventario", "ClaseActivo")
    for codigo, nombre, prefijo, color, orden, modelo in CLASES_INICIALES:
        ClaseActivo.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "prefijo_id": prefijo,
                "color": color,
                "orden": orden,
                "modelo_detalle": modelo,
                "activo": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0007_registrointegridad"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClaseActivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(help_text="Ej: INFRA, SERV", max_length=6, unique=True)),
                ("nombre", models.CharField(max_length=120)),
                ("prefijo_id", models.CharField(help_text="Prefijo del ID (RED, SIS, PC…)", max_length=6)),
                ("color", models.CharField(default="#6b7280", max_length=7)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("activo", models.BooleanField(default=True)),
                ("modelo_detalle", models.CharField(
                    choices=[
                        ("infraestructura", "Infraestructura de red"),
                        ("sistema", "Sistema de información"),
                        ("equipo", "Equipo de cómputo"),
                        ("generico", "Campos libres (JSON)"),
                        ("ninguno", "Solo campos comunes"),
                    ],
                    default="ninguno",
                    max_length=20,
                )),
                ("detalle_schema", models.JSONField(blank=True, default=dict, help_text="Esquema opcional de campos para clases genéricas.")),
            ],
            options={
                "verbose_name": "Clase de activo",
                "verbose_name_plural": "Clases de activo",
                "ordering": ["orden", "codigo"],
            },
        ),
        migrations.CreateModel(
            name="HistoricalClaseActivo",
            fields=[
                ("id", models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name="ID")),
                ("codigo", models.CharField(db_index=True, help_text="Ej: INFRA, SERV", max_length=6)),
                ("nombre", models.CharField(max_length=120)),
                ("prefijo_id", models.CharField(help_text="Prefijo del ID (RED, SIS, PC…)", max_length=6)),
                ("color", models.CharField(default="#6b7280", max_length=7)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("activo", models.BooleanField(default=True)),
                ("modelo_detalle", models.CharField(
                    choices=[
                        ("infraestructura", "Infraestructura de red"),
                        ("sistema", "Sistema de información"),
                        ("equipo", "Equipo de cómputo"),
                        ("generico", "Campos libres (JSON)"),
                        ("ninguno", "Solo campos comunes"),
                    ],
                    default="ninguno",
                    max_length=20,
                )),
                ("detalle_schema", models.JSONField(blank=True, default=dict, help_text="Esquema opcional de campos para clases genéricas.")),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_type", models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1)),
                ("history_user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="auth.user")),
            ],
            options={
                "verbose_name": "historical Clase de activo",
                "verbose_name_plural": "historical Clases de activo",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name="activo",
            name="detalle_extra",
            field=models.JSONField(blank=True, default=dict, verbose_name="Detalle adicional (clases genéricas)"),
        ),
        migrations.AddField(
            model_name="historicalactivo",
            name="detalle_extra",
            field=models.JSONField(blank=True, default=dict, verbose_name="Detalle adicional (clases genéricas)"),
        ),
        migrations.RunPython(poblar_clases, migrations.RunPython.noop),
    ]
