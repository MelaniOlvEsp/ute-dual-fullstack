"""C15: PostgreSQL nuevo + archivos locales sintéticos; nunca usa la configuración de la aplicación.

Ejecutar exclusivamente con C15_TEST_DSN dirigido al contenedor temporal ute-dual-c15-postgres,
base ute_dual_c15_test vacía. Instala el esquema y las migraciones reales una sola vez.
"""
import asyncio
import os
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ute-api-backend'))
from app.application.errors import ApplicationError
from app.application.use_cases.dual import purgas
from app.infrastructure.database.repository import QueryCursorAdapter

DSN = os.environ.get('C15_TEST_DSN', '')


class Database:
    fail_archive_commit = False

    @asynccontextmanager
    async def transaction(self):
        async with await psycopg.AsyncConnection.connect(DSN, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                adapter = QueryCursorAdapter(cur)
                archived = False
                original = adapter.execute
                async def execute(query, params=None):
                    nonlocal archived
                    archived |= query == 'dual.purgas.archivar_documento'
                    return await original(query, params)
                adapter.execute = execute
                yield adapter
                if archived and self.fail_archive_commit:
                    self.fail_archive_commit = False
                    raise OSError('Fallo simulado antes de confirmar el archivado')
        # El contexto psycopg confirma o revierte realmente, también ante CancelledError.

    read = transaction


@unittest.skipUnless(DSN, 'Requiere PostgreSQL temporal C15; no usar la base del piloto')
class PurgasPostgresTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cfg = conninfo_to_dict(DSN)
        if cfg.get('host') != 'ute-dual-c15-postgres' or cfg.get('dbname') != 'ute_dual_c15_test':
            raise RuntimeError('Destino no autorizado: solo el contenedor y base aislados de C15')
        with psycopg.connect(DSN, autocommit=True) as conn:
            if conn.execute('SELECT current_database()').fetchone()[0] != 'ute_dual_c15_test':
                raise RuntimeError('Base inesperada')
            files = [ROOT / 'database/schema_dual_desde_cero.sql',
                     *sorted((ROOT / 'database/migrations').glob('*.sql'))]
            for file in files:
                conn.execute(file.read_text(encoding='utf-8-sig'))

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = Database()
        self.calls = []
        self.runtime = SimpleNamespace(database=self.db, services=SimpleNamespace(purgar_documento=self.delete))

    async def delete(self, key):
        self.calls.append(key)
        (self.folder / key).unlink(missing_ok=True)

    async def fixture(self, deadline="now() - interval '1 second'", attempts=0):
        # deadline procede solo de literales de estas pruebas, nunca de entradas externas.
        self.user, self.period, self.package, self.purge = (uuid4() for _ in range(4))
        self.docs = sorted([uuid4().hex + '.pdf', uuid4().hex + '.pdf'])
        for key in self.docs:
            (self.folder / key).write_bytes(b'%PDF-sintetico')
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            await conn.execute("INSERT INTO usuarios(id,email,password_hash,roles) VALUES (%s,%s,'no-login','{\"tutor_academico\":true}')",
                               (self.user, f'{self.user}@example.invalid'))
            year = 2000 + (await (await conn.execute('SELECT count(*) FROM ciclos_dual')).fetchone())[0]
            await conn.execute('INSERT INTO ciclos_dual(id,cuatrimestre) VALUES (%s,%s)', (self.period, f'Enero-Abril {year}'))
            await conn.execute("""INSERT INTO paquetes_archivo
                (id,alcance,periodo_id,carrera,rol,generado_por,manifiesto_sha256,alumnos,archivos,bytes)
                VALUES (%s,'carrera',%s,'TII','tutor',%s,%s,1,2,26)""", (self.package, self.period, self.user, 'a' * 64))
            await conn.execute(f"""INSERT INTO purgas_archivo
                (id,periodo_id,alcance,carrera,paquete_id,manifiesto_sha256,solicitada_por,
                 solicitada_en,ejecutar_en,archivos,bytes,intentos)
                VALUES (%s,%s,'carrera','TII',%s,%s,%s,now()-interval '7 days', {deadline},2,26,%s)""",
                (self.purge, self.period, self.package, 'a' * 64, self.user, attempts))
            for key in self.docs:
                await conn.execute("""INSERT INTO documentos(clave,tamano,sha256,paginas,subido_por,purga_id)
                    VALUES (%s,13,%s,1,%s,%s)""", (key, 'b' * 64, self.user, self.purge))

    async def snapshot(self):
        async with await psycopg.AsyncConnection.connect(DSN, row_factory=dict_row) as conn:
            purge = await (await conn.execute('SELECT * FROM purgas_archivo WHERE id=%s', (self.purge,))).fetchone()
            docs = await (await conn.execute('SELECT * FROM documentos WHERE clave=ANY(%s) ORDER BY clave', (self.docs,))).fetchall()
            return purge, docs

    async def cancel(self):
        return await purgas.cancelar(self.period, self.purge, {'id': self.user}, runtime=self.runtime)

    async def reject_cancel(self):
        with self.assertRaises(ApplicationError) as caught:
            await self.cancel()
        self.assertEqual(caught.exception.status_code, 409)
        self.assertTrue(all(d['purga_id'] == self.purge for d in (await self.snapshot())[1]))

    async def finish(self):
        self.runtime.services.purgar_documento = self.delete
        result = await purgas.ejecutar_purga(self.runtime, self.purge)
        self.assertEqual((result['archivos'], result['bytes']), (2, 26))
        p, docs = await self.snapshot()
        self.assertEqual(p['estado'], 'completada')
        self.assertIsNone(p['ultimo_error'])
        self.assertTrue(all(d['archivado_en'] and d['purga_id'] == self.purge for d in docs))
        self.assertTrue(all(d['sha256'] == 'b' * 64 and d['tamano'] == 13 for d in docs))
        self.assertEqual(list(self.folder.iterdir()), [])

    async def test_second_file_failure_cannot_be_cancelled_and_retry_preserves_progress(self):
        await self.fixture()
        async def fail_second(key):
            if key == self.docs[1]:
                raise OSError('fallo del segundo archivo')
            await self.delete(key)
        self.runtime.services.purgar_documento = fail_second
        with self.assertRaises(OSError):
            await purgas.ejecutar_purga(self.runtime, self.purge)
        p, docs = await self.snapshot()
        self.assertEqual((p['estado'], p['intentos']), ('programada', 1))
        self.assertIsNotNone(docs[0]['archivado_en'])
        self.assertIsNone(docs[1]['archivado_en'])
        await self.reject_cancel()
        await self.finish()
        self.assertEqual(self.calls.count(self.docs[0]), 1, 'El progreso confirmado no se vuelve a borrar')
        self.assertEqual((await self.snapshot())[0]['intentos'], 2)

    async def test_grace_cancel_is_idempotent_and_prevents_execution(self):
        await self.fixture("now() + interval '7 days'")
        self.assertIsNone(await purgas.ejecutar_purga(self.runtime, self.purge))
        self.assertFalse((await self.cancel())['repetido'])
        self.assertTrue((await self.cancel())['repetido'])
        self.assertIsNone(await purgas.ejecutar_purga(self.runtime, self.purge))
        self.assertEqual(len(list(self.folder.iterdir())), 2)
        self.assertTrue(all(d['purga_id'] is None and d['archivado_en'] is None for d in (await self.snapshot())[1]))

    async def test_exact_deadline_rejects_cancel_even_without_attempts(self):
        await self.fixture('now()')
        await self.reject_cancel()

    async def test_started_attempt_cannot_cancel_even_if_deadline_is_in_future(self):
        await self.fixture("now() + interval '7 days'", attempts=1)
        await self.reject_cancel()

    async def test_deadline_is_checked_after_waiting_for_row_lock(self):
        await self.fixture("now() + interval '0.2 second'")
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            await conn.execute('SELECT id FROM purgas_archivo WHERE id=%s FOR UPDATE', (self.purge,))
            cancel = asyncio.create_task(self.reject_cancel())
            await asyncio.sleep(0.3)
        await cancel

    async def test_commit_failure_after_delete_retries_missing_file_and_keeps_intention(self):
        await self.fixture()
        self.db.fail_archive_commit = True
        with self.assertRaises(OSError):
            await purgas.ejecutar_purga(self.runtime, self.purge)
        self.assertFalse((self.folder / self.docs[0]).exists())
        self.assertIsNone((await self.snapshot())[1][0]['archivado_en'])
        self.assertEqual((await self.snapshot())[0]['intentos'], 1)
        await self.reject_cancel()
        await self.finish()
        self.assertEqual(self.calls.count(self.docs[0]), 2)

    async def test_task_interruption_keeps_committed_progress_and_can_resume(self):
        await self.fixture()
        async def interrupted(key):
            if key == self.docs[1]:
                raise asyncio.CancelledError()
            await self.delete(key)
        self.runtime.services.purgar_documento = interrupted
        with self.assertRaises(asyncio.CancelledError):
            await purgas.ejecutar_purga(self.runtime, self.purge)
        self.assertIsNotNone((await self.snapshot())[1][0]['archivado_en'])
        await self.reject_cancel()
        await self.finish()

    async def test_parallel_worker_skips_locked_file_and_cancel_cannot_release_it(self):
        await self.fixture()
        started, release = asyncio.Event(), asyncio.Event()
        async def slow_delete(key):
            if key == self.docs[0]:
                started.set()
                await release.wait()
            await self.delete(key)
        self.runtime.services.purgar_documento = slow_delete
        worker = asyncio.create_task(purgas.ejecutar_purga(self.runtime, self.purge))
        await asyncio.wait_for(started.wait(), 5)
        try:
            other = await asyncio.wait_for(purgas.ejecutar_purga(self.runtime, self.purge), 5)
            self.assertIsNone(other)
            cancel = asyncio.create_task(self.reject_cancel())
        finally:
            release.set()
        result = await asyncio.wait_for(worker, 5)
        await asyncio.wait_for(cancel, 5)
        # La cancelación puede tomar brevemente el bloqueo entre dos documentos. El trabajador
        # cede con SKIP LOCKED; la intención persiste y el siguiente ciclo termina lo pendiente.
        if result is None:
            await self.finish()
        else:
            self.assertEqual(result['archivos'], 2)
        self.assertEqual(self.calls, self.docs)
        self.assertEqual((await self.snapshot())[0]['estado'], 'completada')


if __name__ == '__main__':
    unittest.main(verbosity=2)
