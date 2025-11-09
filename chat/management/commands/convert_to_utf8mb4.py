from django.core.management.base import BaseCommand, CommandError
from django.db import connection, DatabaseError
import sys


class Command(BaseCommand):
    help = (
        'Helper to convert the current MySQL database and its tables to utf8mb4. '
        'This command prints the ALTER statements and can execute them when --execute is passed. '
        'Requires appropriate DB privileges. Run a backup first.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true', help='Execute the ALTER statements. By default only prints (dry-run).')
        parser.add_argument('--yes', action='store_true', help='Assume yes for confirmations when executing.')

    def handle(self, *args, **options):
        engine = connection.settings_dict.get('ENGINE', '')
        if 'mysql' not in engine.lower():
            raise CommandError('This command is intended for MySQL/MariaDB databases only.')

        db_name = connection.settings_dict.get('NAME')
        if not db_name:
            raise CommandError('Cannot determine database NAME from settings.')

        self.stdout.write(self.style.NOTICE(f'Current DB: {db_name}'))
        self.stdout.write('Generating ALTER statements...')

        alter_db = f"ALTER DATABASE `{db_name}` CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;"

        # Fetch tables from information_schema to preserve proper ordering
        with connection.cursor() as cur:
            cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE';", [db_name])
            rows = cur.fetchall()

        tables = [r[0] for r in rows]
        if not tables:
            self.stdout.write(self.style.WARNING('No tables found in the database.'))
            return

        alter_tables = [f"ALTER TABLE `{t}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" for t in tables]

        self.stdout.write('\n--- SQL Statements to run ---')
        self.stdout.write(alter_db)
        for s in alter_tables:
            self.stdout.write(s)
        self.stdout.write('--- end ---\n')

        if not options['execute']:
            self.stdout.write(self.style.SUCCESS('Dry-run complete. Re-run with --execute to apply the changes.'))
            return

        # Confirm
        if not options['yes']:
            self.stdout.write(self.style.WARNING('About to execute the statements above. This can be destructive. Make sure you have a DB backup.'))
            confirm = input('Proceed and execute ALTER statements? (yes/NO): ')
            if confirm.strip().lower() not in ('y', 'yes'):
                self.stdout.write(self.style.ERROR('Aborted by user.'))
                return

        # Execute
        try:
            with connection.cursor() as cur:
                self.stdout.write('Executing: ' + alter_db)
                cur.execute(alter_db)
                for s in alter_tables:
                    self.stdout.write('Executing: ' + s)
                    cur.execute(s)
        except DatabaseError as e:
            raise CommandError(f'Database error during conversion: {e}')

        self.stdout.write(self.style.SUCCESS('Database and tables converted to utf8mb4 (if supported).'))
