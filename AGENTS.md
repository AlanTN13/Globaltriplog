# GlobalTrip Cotizador — Entrada de agentes

Las instrucciones superiores de la plataforma y los controles reales de acceso prevalecen siempre.

## Gobierno AlanOS

Antes de trabajo sustantivo, leer por una vía autorizada la versión vigente de `Alan/01_Architecture/Execution_Runtime_Contract.md` en `AlanTN13/Alanos` y registrar la revisión consultada.

URL canónica: https://github.com/AlanTN13/Alanos/blob/main/Alan/01_Architecture/Execution_Runtime_Contract.md

Contexto relevante:
- `Alan/04_Clientes NexOps/Global_Trip/`;
- `Alan/04_Clientes NexOps/GlobalTrip/`;

Un enlace no se carga solo. Si el contrato o el contexto necesario no están accesibles, declarar `BLOCKED_EXTERNAL` y no iniciar cambios. No reconstruir reglas de memoria ni ampliar exploración por reflejo. Una sesión ya abierta no se da por actualizada.

El estado vigente/legacy de esta superficie debe verificarse antes de modificarla. No asumir producción o autoridad sobre otros componentes de GlobalTrip por existir este repositorio.

## Preflight

Antes de modificar, registrar en la evidencia existente:

```text
EXECUTION PREFLIGHT
Rol y superficie real:
Resultado y autorización:
Contexto verificado / revisión:
Budget / tipo / riesgo:
Dentro y fuera de alcance:
Aceptación y validaciones:
Permisos de producción / recuperación:
STOP y señal de BUDGET_RISK:
```

## Límites

- Consulta, auditoría o asunción de rol no equivalen a autorización de ejecución.
- Leer sólo lo necesario para el resultado aprobado.
- Hallazgos laterales no amplían el alcance automáticamente.
- Un defecto que invalida aceptación o seguridad impide declarar éxito.
- No cambiar producción, datos reales, credenciales, permisos, pricing, compromisos comerciales ni sistemas externos sin el gate correspondiente.
- Separar implementado, mergeado, desplegado y validado por cliente.
- No redefinir negocio desde el repositorio técnico.

## Cierre

Toda entrega no trivial deja evidencia durable y `EXECUTION RECEIPT`/checkpoint conforme al contrato vigente, incluyendo validaciones realmente ejecutadas, hallazgos diferidos, recuperación y STOP.
