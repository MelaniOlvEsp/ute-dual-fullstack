"""Apoyo común de los smokes para el ciclo de vida de los períodos (C07).

Un período cerrado no se reabre por la API (estados sin retroceso), pero cada smoke necesita uno
con la recepción abierta. Por eso cada corrida cierra el período por la API al terminar y la
siguiente, si lo encuentra cerrado y sin finalizar, restablece su estado con SQL como preparación
de la prueba (equivale a una instalación limpia). Un período finalizado nunca se restablece.
"""
from __future__ import annotations

from local_admin import connect_local


def listar(client, headers):
    respuesta = client.get("/dual/tutor/periodos", headers=headers)
    assert respuesta.status_code == 200, respuesta.text[:200]
    return respuesta.json()


def por_etiqueta(client, headers, etiqueta):
    return next((p for p in listar(client, headers) if p["cuatrimestre"] == etiqueta), None)


def cerrar(client, headers, periodo_id, esperado=200):
    respuesta = client.post(f"/dual/tutor/periodos/{periodo_id}/cierre-recepcion", headers=headers,
                            json={"confirmar": True})
    assert respuesta.status_code == esperado, (esperado, respuesta.status_code, respuesta.text[:200])
    return respuesta.json()


def cerrar_abiertos(client, headers, excepto=None):
    for periodo in listar(client, headers):
        if periodo["recepcion"] == "abierta" and periodo["cuatrimestre"] != excepto:
            cerrar(client, headers, periodo["id"])


def abrir_de_prueba(client, headers, etiqueta, inicio, fin):
    """Deja abierto solo el período indicado y devuelve su ID."""
    cerrar_abiertos(client, headers, excepto=etiqueta)
    periodo = por_etiqueta(client, headers, etiqueta)
    if periodo and periodo["recepcion"] == "abierta":
        return periodo["id"]
    if periodo and periodo["recepcion"] == "cerrada":
        assert periodo["evaluacion"] != "finalizada", "Un período finalizado no se restablece"
        with connect_local() as conn:
            conn.execute(
                "UPDATE ciclos_dual SET cerrado = FALSE, abierto = FALSE, cerrado_por = NULL, cerrado_at = NULL "
                "WHERE id = %s AND evaluacion_finalizada_en IS NULL", (periodo["id"],))
            conn.commit()
    respuesta = client.post("/dual/tutor/abrir-cuatrimestre", headers=headers, json={
        "periodo_label": etiqueta, "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat()})
    assert respuesta.status_code == 200, respuesta.text[:200]
    return por_etiqueta(client, headers, etiqueta)["id"]
