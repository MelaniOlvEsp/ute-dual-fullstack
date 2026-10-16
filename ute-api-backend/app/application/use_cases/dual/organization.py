from __future__ import annotations

import csv
import io

from app.application.errors import ApplicationError


MAX_CSV_ROWS = 500


def _valid_matricula(value: str) -> bool:
    # isdigit() acepta dígitos Unicode (p. ej. superíndices); exigir ASCII.
    return value.isascii() and value.isdigit() and len(value) == 9


def parse_student_csv(content: bytes) -> list[dict]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ApplicationError(422, "El archivo no tiene codificación UTF-8 válida.") from exc

    reader = csv.DictReader(io.StringIO(text))
    headers = [item.strip().lower() for item in (reader.fieldnames or [])]
    if headers != ["matricula", "nombre"]:
        raise ApplicationError(422, 'El CSV debe tener exactamente las columnas "matricula,nombre".')

    rows = []
    seen = set()
    for line, raw in enumerate(reader, start=2):
        matricula = (raw.get("matricula") or "").strip()
        nombre = (raw.get("nombre") or "").strip()
        if not matricula and not nombre:
            continue
        if len(rows) >= MAX_CSV_ROWS:
            raise ApplicationError(422, f"El CSV admite como máximo {MAX_CSV_ROWS} filas.")
        reason = None
        if not _valid_matricula(matricula):
            reason = "La matrícula debe contener exactamente 9 dígitos."
        elif not nombre:
            reason = "El nombre no puede estar vacío."
        elif matricula in seen:
            reason = "La matrícula está repetida dentro del archivo."
        seen.add(matricula)
        rows.append({"fila": line, "matricula": matricula, "nombre": nombre, "razon": reason})
    return rows


async def list_careers(user, *, runtime):
    async with runtime.database.read() as cur:
        await cur.execute("dual.organization.careers")
        return [dict(row) for row in await cur.fetchall()]


async def _analyze(cur, group_id, period_id, rows):
    await cur.execute("dual.organization.group_period", (group_id, period_id))
    context = await cur.fetchone()
    if not context:
        raise ApplicationError(404, "Grupo o período no encontrado")

    valid_rows = [row for row in rows if not row.get("razon")]
    matriculas = [row["matricula"] for row in valid_rows]
    existing = {}
    if matriculas:
        await cur.execute("dual.organization.students_for_period", (period_id, matriculas))
        existing = {row["matricula"]: dict(row) for row in await cur.fetchall()}

    valid, repeated, errors = [], [], []
    for row in rows:
        if row.get("razon"):
            errors.append({key: row[key] for key in ("fila", "matricula", "razon")})
            continue
        current = existing.get(row["matricula"])
        if current and current["nombre"].strip().casefold() != row["nombre"].strip().casefold():
            errors.append({"fila": row["fila"], "matricula": row["matricula"],
                           "razon": "La matrícula ya existe con un nombre diferente."})
        elif current and current.get("grupo_id") and str(current["grupo_id"]) != str(group_id):
            errors.append({"fila": row["fila"], "matricula": row["matricula"],
                           "razon": f"Ya pertenece a {current['nomenclatura']} en este período."})
        elif current and current.get("grupo_id"):
            repeated.append({"matricula": row["matricula"], "nombre": row["nombre"]})
        else:
            valid.append({"matricula": row["matricula"], "nombre": row["nombre"],
                          "existente": bool(current)})
    return dict(context), valid, repeated, errors


async def preview_csv(group_id, period_id, file, user, *, runtime):
    rows = parse_student_csv(await file.read())
    async with runtime.database.read() as cur:
        context, valid, repeated, errors = await _analyze(cur, group_id, period_id, rows)
    return {"grupo": context["nomenclatura"], "periodo": context["periodo_label"],
            "validos": valid, "repetidos": repeated, "errores": errors,
            "puede_aplicar": bool(valid) and not errors}


async def apply_csv(group_id, period_id, file, user, *, runtime):
    rows = parse_student_csv(await file.read())
    async with runtime.database.transaction() as cur:
        _, valid, repeated, errors = await _analyze(cur, group_id, period_id, rows)
        if errors:
            raise ApplicationError(409, {"mensaje": "El lote contiene conflictos; no se aplicó ninguna fila.",
                                         "errores": errors})
        inserted = []
        for row in valid:
            if not row["existente"]:
                await cur.execute("dual.organization.insert_student",
                                  (row["matricula"], row["nombre"],
                                   f"{row['matricula']}@ute.edu.mx", group_id))
                await cur.fetchone()
                inserted.append({"matricula": row["matricula"], "nombre": row["nombre"]})
            else:
                await cur.execute("dual.organization.authorize_student", (row["matricula"],))
            await cur.execute("dual.organization.insert_membership",
                              (row["matricula"], group_id, period_id, user["id"]))
            if not await cur.fetchone():
                raise ApplicationError(409, "La pertenencia cambió concurrentemente; no se aplicó el lote.")
            await cur.execute("dual.organization.set_current_group",
                              (row["matricula"], row["matricula"]))
    return {"insertados": inserted,
            "actualizados": [{"matricula": row["matricula"], "nombre": row["nombre"]}
                              for row in valid if row["existente"]],
            "repetidos": repeated, "errores": []}


async def add_student(group_id, data, user, *, runtime):
    row = {"fila": 1, "matricula": data.matricula.strip(), "nombre": data.nombre.strip(), "razon": None}
    if not _valid_matricula(row["matricula"]):
        raise ApplicationError(422, "La matrícula debe contener exactamente 9 dígitos.")
    if not row["nombre"]:
        raise ApplicationError(422, "El nombre no puede estar vacío.")
    async with runtime.database.transaction() as cur:
        _, valid, repeated, errors = await _analyze(cur, group_id, data.periodo_id, [row])
        if errors:
            raise ApplicationError(409, errors[0]["razon"])
        if repeated:
            return {**repeated[0], "grupo_id": group_id, "repetido": True}
        item = valid[0]
        if not item["existente"]:
            await cur.execute("dual.organization.insert_student",
                              (item["matricula"], item["nombre"],
                               f"{item['matricula']}@ute.edu.mx", group_id))
            await cur.fetchone()
        else:
            await cur.execute("dual.organization.authorize_student", (item["matricula"],))
        await cur.execute("dual.organization.insert_membership",
                          (item["matricula"], group_id, data.periodo_id, user["id"]))
        if not await cur.fetchone():
            raise ApplicationError(409, "La pertenencia cambió concurrentemente.")
        await cur.execute("dual.organization.set_current_group",
                          (item["matricula"], item["matricula"]))
    return {"matricula": item["matricula"], "nombre": item["nombre"],
            "grupo_id": group_id, "repetido": False}


async def membership_history(matricula, user, *, runtime):
    async with runtime.database.read() as cur:
        await cur.execute("dual.organization.history", (matricula,))
        return [dict(row) for row in await cur.fetchall()]


async def preview_promotion(data, user, *, runtime):
    selected = data.matriculas or None
    async with runtime.database.read() as cur:
        await cur.execute("dual.organization.group_period", (data.grupo_destino_id, data.periodo_destino_id))
        target = await cur.fetchone()
        if not target:
            raise ApplicationError(404, "Grupo o período destino no encontrado")
        await cur.execute("dual.organization.source_members",
                          (data.grupo_origen_id, data.periodo_origen_id, selected, selected))
        source = [dict(row) for row in await cur.fetchall()]
        if not source:
            raise ApplicationError(404, "No hay alumnos seleccionados en el grupo y período origen")
        rows = [{"fila": index, "matricula": item["matricula"], "nombre": item["nombre"], "razon": None}
                for index, item in enumerate(source, start=1)]
        _, valid, repeated, errors = await _analyze(
            cur, data.grupo_destino_id, data.periodo_destino_id, rows)
    return {"grupo_destino": dict(target)["nomenclatura"], "validos": valid,
            "repetidos": repeated, "errores": errors,
            "puede_aplicar": bool(valid) and not errors}


async def apply_promotion(data, user, *, runtime):
    preview = await preview_promotion(data, user, runtime=runtime)
    if preview["errores"]:
        raise ApplicationError(409, {"mensaje": "La promoción tiene conflictos; no se aplicó.",
                                     "errores": preview["errores"]})
    async with runtime.database.transaction() as cur:
        for item in preview["validos"]:
            await cur.execute("dual.organization.insert_membership",
                              (item["matricula"], data.grupo_destino_id,
                               data.periodo_destino_id, user["id"]))
            if not await cur.fetchone():
                raise ApplicationError(409, "La promoción cambió concurrentemente; no se aplicó.")
            await cur.execute("dual.organization.set_current_group",
                              (item["matricula"], item["matricula"]))
    return {"promovidos": preview["validos"], "repetidos": preview["repetidos"]}
