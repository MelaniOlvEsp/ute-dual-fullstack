"""C02 HTTP/PostgreSQL real. Solo base local C01; conserva fixtures sintéticos.
Ocho logins: ejecutar sin otros intentos desde este contenedor durante la ventana.
No imprime contraseñas/tokens ni elimina datos.
"""
import os
import secrets
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx
from local_admin import connect_local, create_coordinator
from app.domain.passwords import validate_password

BASE = os.environ.get('API_URL', 'http://api:8000')
if BASE not in ('http://api:8000', 'http://127.0.0.1:8001'):
    raise SystemExit('Destino HTTP no permitido para C02')


def expect(response, status):
    if response.status_code != status:
        raise AssertionError(f'{response.request.method} {response.request.url.path}: esperado {status}, recibido {response.status_code}')
    return response.json()


def concurrent_posts(path, body, headers=None):
    barrier = Barrier(2)
    def post():
        with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
            barrier.wait(timeout=10)
            return client.post(path, json=body, headers=headers)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: post(), range(2)))
    assert sorted(r.status_code for r in results) == [201, 409], 'Alta concurrente debe producir 201 y 409'
    return next(r.json() for r in results if r.status_code == 201)


def main():
    suffix = secrets.token_hex(5)
    password = 'C02a' + secrets.token_urlsafe(20)
    changed = 'C02b' + secrets.token_urlsafe(20)
    restored = 'C02c' + secrets.token_urlsafe(20)
    admin_email = f'c02.{suffix}@ute.edu.mx'
    tutor_email = f't02.{suffix}@ute.edu.mx'
    # Evita colisiones entre matrículas de esta ejecución.
    numbers = set()
    while len(numbers) < 4:
        numbers.add(str(secrets.randbelow(900000000) + 100000000))
    a, b, blocked, mismatch = sorted(numbers)
    os.environ['LOCAL_ADMIN_PASSWORD'] = password
    create_coordinator(admin_email, 'Coordinador sintético C02')
    with connect_local() as conn:
        group = conn.execute("INSERT INTO grupos (plan,carrera,carrera_id,zona,modalidad,cuatrimestre,letra,ciclo_ingreso) VALUES ('26','ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',(SELECT id FROM carreras WHERE codigo='TII'),1,'intensivo',1,'A',%s) RETURNING id", (suffix,)).fetchone()[0]
        for number in (a, b, blocked, mismatch):
            email = f'{number}@ute.edu.mx' if number != mismatch else f'mismatch.{suffix}@ute.edu.mx'
            conn.execute('INSERT INTO alumnos (matricula,nombre,email,grupo_id,registro_dual_autorizado) VALUES (%s,%s,%s,%s,%s)',
                         (number, 'Alumno sintético C02', email, group, number != blocked))
        for number in (a, b):
            conn.execute("INSERT INTO alumnos_dual (matricula,cuatrimestre,fecha_inicio) VALUES (%s,'Septiembre-Diciembre 2026',CURRENT_DATE)", (number,))
    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
        def login(email, secret):
            result = expect(client.post('/auth/login', json={'email': email, 'password': secret}), 200)
            return {'Authorization': 'Bearer ' + result['access_token']}
        expect(client.get('/health'), 200)
        admin_temp = login(admin_email, password)
        expect(client.get('/auth/me', headers=admin_temp), 403)
        expect(client.post('/auth/cambiar-password', headers=admin_temp, json={'password_actual': password, 'password_nueva': changed}), 200)
        admin = login(admin_email, changed)
        expect(client.get('/auth/me', headers=admin_temp), 401)
        created = concurrent_posts('/auth/tutores', {'nombre': 'Tutor sintético C02', 'email': tutor_email}, admin)
        validate_password(created['password_temporal'])
        tutor_temp = login(tutor_email, created['password_temporal'])
        expect(client.get('/auth/me', headers=tutor_temp), 403)
        expect(client.post('/auth/cambiar-password', headers=tutor_temp, json={'password_actual': created['password_temporal'], 'password_nueva': changed}), 200)
        tutor = login(tutor_email, changed)
        tutor_id = expect(client.get('/auth/me', headers=tutor), 200)['id']
        expect(client.get('/auth/tutores', headers=tutor), 403)
        for number in (blocked, mismatch):
            expect(client.post('/auth/register', json={'email': f'{number}@ute.edu.mx', 'password': password}), 403)
        expect(client.post('/auth/register', json={'email': f'{a}@ute.edu.mx', 'password': password, 'roles': {'coordinador_dual': True}}), 422)
        expect(client.post('/auth/register', json={'email': f'{a}@ute.edu.mx', 'password': 'Aa1' + 'x' * 70}), 400)
        concurrent_posts('/auth/register', {'email': f'{a}@ute.edu.mx', 'password': password})
        expect(client.post('/auth/register', json={'email': f'{b}@ute.edu.mx', 'password': password}), 201)
        student = login(f'{a}@ute.edu.mx', password)
        other = login(f'{b}@ute.edu.mx', password)
        student_id = expect(client.get('/auth/me', headers=student), 200)['id']
        assert expect(client.get('/auth/me', headers=student), 200)['roles'] == {'alumno': True, 'tutor_academico': False, 'coordinador_dual': False}
        # Wrong current password is an input error, not an expired session.
        expect(client.post('/auth/cambiar-password', headers=student, json={'password_actual': 'IncorrectPassword123', 'password_nueva': changed}), 400)
        expect(client.get('/auth/me', headers=student), 200)
        with connect_local() as conn:
            report_a = conn.execute("INSERT INTO reportes_dual (matricula,cuatrimestre,semana,calificacion_alumno,estado,revisado_por) VALUES (%s,'Septiembre-Diciembre 2026',1,8,'Aprobada',%s) RETURNING id", (a, tutor_id)).fetchone()[0]
            report_b = conn.execute("INSERT INTO reportes_dual (matricula,cuatrimestre,semana,calificacion_alumno,estado) VALUES (%s,'Septiembre-Diciembre 2026',1,9,'Aprobada') RETURNING id", (b,)).fetchone()[0]
        # C08: el alumno solo consulta su propio expediente (la matrícula sale de la sesión).
        assert expect(client.get('/dual/alumno/expediente', headers=student), 200)['alumno']['matricula'] == a
        expect(client.get(f'/dual/alumno/reportes/{report_b}/versiones/1/pdf', headers=student), 404)
        expect(client.get(f'/dual/alumno/reportes/{report_a}/versiones/1/pdf', headers=other), 404)
        expect(client.get(f'/dual/carrera/alumnos/{b}/expediente', headers=student), 403)
        expect(client.patch(f'/dual/carrera/alumnos/{b}', headers=student, json={'nombre': 'No autorizado'}), 403)
        expect(client.delete(f'/dual/carrera/alumnos/{b}', headers=student), 403)
        expect(client.get(f'/dual/carrera/alumnos/{a}/expediente', headers=tutor), 200)
        expect(client.get(f'/dual/carrera/alumnos/{b}/expediente', headers=admin), 200)
        # C07 (MP-11): el cierre es del coordinador, por ID de período; tutor y alumno reciben 403.
        periodo_ajeno = '00000000-0000-0000-0000-000000000001'
        expect(client.post(f'/dual/tutor/periodos/{periodo_ajeno}/cierre-recepcion', headers=tutor, json={'confirmar': True}), 403)
        expect(client.post(f'/dual/tutor/periodos/{periodo_ajeno}/finalizacion', headers=tutor, json={'confirmar': True}), 403)
        expect(client.post(f'/dual/tutor/periodos/{periodo_ajeno}/cierre-recepcion', headers=student, json={'confirmar': True}), 403)
        expect(client.get(f'/dual/carrera/paquetes/alumno/{b}', headers=student, params={'periodo_id': periodo_ajeno}), 403)
        expect(client.get('/dual/carrera/paquetes/carrera/TII', headers=student, params={'periodo_id': periodo_ajeno}), 403)
        message = expect(client.post('/foro/buzon/', headers=student, json={'area':'dual','asunto':'Smoke C02','mensaje':'Mensaje sintético'}), 201)
        mid = message['id']
        expect(client.get(f'/foro/buzon/{mid}', headers=other), 404)
        expect(client.post(f'/foro/buzon/{mid}/respuestas', headers=other, json={'texto':'No autorizado'}), 404)
        expect(client.patch(f'/foro/buzon/{mid}/cerrar', headers=student), 403)
        expect(client.patch(f'/foro/buzon/{mid}/leido', headers=student), 403)
        expect(client.get(f'/foro/buzon/{mid}', headers=tutor), 200)
        expect(client.get(f'/foro/buzon/{mid}', headers=admin), 200)
        expect(client.post('/foro/publicaciones', headers=student, json={'contenido':'No autorizado'}), 403)
        reset_path = f'/auth/alumnos/{a}/password-provisional'
        expect(client.post(reset_path, headers=admin), 403)
        expect(client.post(reset_path, headers=other), 403)
        temporary = expect(client.post(reset_path, headers=tutor), 200)['password_temporal']
        validate_password(temporary)
        expect(client.get('/auth/me', headers=student), 401)
        reset_session = login(f'{a}@ute.edu.mx', temporary)
        expect(client.get('/dual/alumno/expediente', headers=reset_session), 403)
        expect(client.post('/auth/cambiar-password', headers=reset_session, json={'password_actual':temporary,'password_nueva':restored}), 200)
        expect(client.get('/auth/me', headers=reset_session), 401)
        student = login(f'{a}@ute.edu.mx', restored)
        expect(client.get('/auth/me', headers=student), 200)
        expect(client.delete(f'/dual/carrera/alumnos/{a}', headers=tutor), 200)
        expect(client.get('/auth/me', headers=student), 401)
        expect(client.delete(f'/auth/tutores/{tutor_id}', headers=admin), 200)
        expect(client.post('/auth/register', json={'email': f'{a}@ute.edu.mx', 'password': password}), 403)
        expect(client.get('/auth/me', headers=tutor), 401)
        with connect_local() as conn:
            assert conn.execute('SELECT activo FROM usuarios WHERE id=%s', (student_id,)).fetchone() == (False,)
            assert conn.execute('SELECT registro_dual_autorizado FROM alumnos WHERE matricula=%s', (a,)).fetchone() == (False,)
            assert conn.execute('SELECT count(*) FROM alumnos_dual WHERE matricula=%s', (a,)).fetchone()[0] == 1
            assert conn.execute('SELECT revisado_por FROM reportes_dual WHERE id=%s', (report_a,)).fetchone()[0] == __import__('uuid').UUID(tutor_id)
            assert conn.execute('SELECT alumno_id FROM buzon_mensajes WHERE id=%s', (mid,)).fetchone()[0] == __import__('uuid').UUID(student_id)
            assert conn.execute('SELECT activo FROM usuarios WHERE id=%s', (tutor_id,)).fetchone() == (False,)
    print('PASS C02: altas concurrentes, registro autorizado, roles, recuperación, revocación, aislamiento de objetos y bajas con referencias conservadas. HTTP/PostgreSQL REALES.')
    print('PDF autorizado/proveedor, calendario e historial integral: NO_VERIFICADA. Fixtures sintéticos conservados.')

if __name__ == '__main__':
    try:
        main()
    except (AssertionError, httpx.HTTPError) as exc:
        print(f'FAIL C02: {exc}', file=sys.stderr)
        raise SystemExit(1)
