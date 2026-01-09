from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.apps import apps
from django.db.utils import OperationalError
import traceback


class Command(BaseCommand):
    help = 'Sincroniza la base de datos espejo con default después de un failover'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se sincronizaría sin hacer cambios reales',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Sincronizar solo una app específica (ej: fiesta)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        app_filter = options.get('app')

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('🔄 INICIANDO SINCRONIZACIÓN DE BASES DE DATOS'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('⚠️  MODO DRY-RUN: No se harán cambios reales'))

        # Verificar conectividad
        if not self._check_databases():
            return

        # Obtener modelos a sincronizar
        models_to_sync = self._get_models(app_filter)

        total_synced = 0
        total_errors = 0

        for model in models_to_sync:
            try:
                synced = self._sync_model(model, dry_run)
                total_synced += synced
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ Error en {model.__name__}: {str(e)}')
                )
                traceback.print_exc()

        # Actualizar secuencias
        if not dry_run and total_synced > 0:
            self._update_sequences(models_to_sync)

        # Resumen final
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✅ Registros sincronizados: {total_synced}'))
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errores encontrados: {total_errors}'))
        self.stdout.write(self.style.WARNING('=' * 70))

    def _check_databases(self):
        """Verifica que ambas bases de datos estén accesibles"""
        self.stdout.write('🔍 Verificando conectividad...')

        for db_name in ['default', 'espejo']:
            try:
                conn = connections[db_name]
                conn.ensure_connection()
                self.stdout.write(
                    self.style.SUCCESS(f'  ✅ {db_name}: Conectada')
                )
            except OperationalError as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ {db_name}: No disponible - {str(e)}')
                )
                return False

        return True

    def _get_models(self, app_filter=None):
        """Obtiene la lista de modelos a sincronizar"""
        models = []

        if app_filter:
            try:
                app_config = apps.get_app_config(app_filter)
                models = list(app_config.get_models())
                self.stdout.write(
                    self.style.NOTICE(f'📦 Sincronizando app: {app_filter}')
                )
            except LookupError:
                self.stdout.write(
                    self.style.ERROR(f'❌ App no encontrada: {app_filter}')
                )
                return []
        else:
            # Sincronizar todas las apps del proyecto (excepto auth, contenttypes, etc)
            exclude_apps = ['auth', 'contenttypes', 'sessions', 'admin', 'messages', 'staticfiles']
            for app_config in apps.get_app_configs():
                if app_config.label not in exclude_apps:
                    models.extend(app_config.get_models())

        self.stdout.write(
            self.style.NOTICE(f'📊 Total de modelos a sincronizar: {len(models)}')
        )
        return models

    def _sync_model(self, model, dry_run=False):
        """Sincroniza un modelo específico"""
        model_name = model.__name__
        self.stdout.write(f'\n🔄 Procesando: {model_name}...')

        # Obtener IDs de ambas bases
        default_ids = set(
            model.objects.using('default').values_list('pk', flat=True)
        )
        espejo_ids = set(
            model.objects.using('espejo').values_list('pk', flat=True)
        )

        # Encontrar registros faltantes en default
        missing_ids = espejo_ids - default_ids

        if not missing_ids:
            self.stdout.write(
                self.style.SUCCESS(f'  ✅ {model_name}: Sincronizado (0 faltantes)')
            )
            return 0

        self.stdout.write(
            self.style.WARNING(f'  ⚠️  {model_name}: {len(missing_ids)} registros faltantes')
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(f'  🔍 IDs faltantes: {sorted(list(missing_ids)[:10])}...')
            )
            return len(missing_ids)

        # Copiar registros faltantes
        synced_count = 0
        for pk in missing_ids:
            try:
                # Obtener el objeto de espejo
                obj = model.objects.using('espejo').get(pk=pk)

                # Extraer datos usando attname (IDs crudos para ForeignKeys)
                data = {}
                for field in obj._meta.fields:
                    data[field.attname] = getattr(obj, field.attname)

                # Insertar en default
                with transaction.atomic(using='default'):
                    model.objects.using('default').create(**data)

                synced_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error copiando {model_name} ID={pk}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'  ✅ {model_name}: {synced_count} registros copiados')
        )
        return synced_count

    def _update_sequences(self, models):
        """Actualiza las secuencias de auto-increment en PostgreSQL"""
        self.stdout.write('\n🔢 Actualizando secuencias de IDs...')

        db_engine = connections['default'].settings_dict['ENGINE']

        if 'postgresql' in db_engine:
            self._update_postgres_sequences(models)
        elif 'mysql' in db_engine:
            self._update_mysql_sequences(models)
        else:
            self.stdout.write(
                self.style.WARNING('  ⚠️  Motor de BD no soportado para actualización de secuencias')
            )

    def _update_postgres_sequences(self, models):
        """Actualiza secuencias en PostgreSQL"""
        with connections['default'].cursor() as cursor:
            for model in models:
                table_name = model._meta.db_table
                pk_field = model._meta.pk.column

                try:
                    # Obtener el máximo ID actual
                    cursor.execute(f"SELECT MAX({pk_field}) FROM {table_name}")
                    max_id = cursor.fetchone()[0]

                    if max_id is not None:
                        # Actualizar la secuencia
                        sequence_name = f"{table_name}_{pk_field}_seq"
                        cursor.execute(
                            f"SELECT setval('{sequence_name}', {max_id}, true)"
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ {table_name}: Secuencia actualizada a {max_id}')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠️  {table_name}: {str(e)}')
                    )

    def _update_mysql_sequences(self, models):
        """Actualiza auto_increment en MySQL"""
        with connections['default'].cursor() as cursor:
            for model in models:
                table_name = model._meta.db_table
                pk_field = model._meta.pk.column

                try:
                    # Obtener el máximo ID actual
                    cursor.execute(f"SELECT MAX({pk_field}) FROM {table_name}")
                    max_id = cursor.fetchone()[0]

                    if max_id is not None:
                        # Actualizar AUTO_INCREMENT
                        next_id = max_id + 1
                        cursor.execute(
                            f"ALTER TABLE {table_name} AUTO_INCREMENT = {next_id}"
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ {table_name}: AUTO_INCREMENT actualizado a {next_id}')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠️  {table_name}: {str(e)}')
                    )
