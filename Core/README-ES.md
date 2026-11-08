# Harnessia Core

[English](README.md)

Harnessia crea espacios de trabajo de IA centrados en una tarea llamados Spaces. Un Space es un pseudoproyecto que mantiene las reglas y capacidades para colaborar con la IA separadas del proyecto real y su documentación anexa. Tú eliges lo que necesita cada Space; Harnessia lo valida y genera la configuración para OpenCode y Claude Code.

Las capacidades permanecen en sus Sources originales. Harnessia las enlaza en lugar de copiarlas o reescribirlas.

**Todo el proyecto Harnessia Core está en `Core/`, incluidas estas guías operativas y la licencia.** Git está un nivel por encima. Solo se versionan `Core/` y el `.gitignore` raíz; cualquier otra carpeta hermana queda excluida por defecto. Salvo indicación contraria, todas las rutas y comandos de esta guía son relativos a `Core/`, no a la raíz del repositorio Git.

`Core/docs/` contiene tanto referencias mantenidas del producto como material de trabajo local. Los archivos de referencia y `docs/adr/` se versionan; las entradas privadas, los resultados locales revisados y el trabajo en curso corresponden, respectivamente, a `docs/sources/`, `docs/deliverables/` y `docs/wip/`. **`Core/.gitignore` excluye esos tres subdirectorios; su contenido nunca se publica.** La configuración del IDE corresponde a `Core/.idea/`, ignorado. Los repositorios de capacidades y las proyecciones de clientes generadas también permanecen en Core.

## Conceptos de un vistazo

| Concepto | Significado |
| --- | --- |
| **Core** | El proyecto central de Harnessia dentro de `Core/`. Contiene el motor, el contexto compartido, los Sources compartidos y la documentación. |
| **Instance** | Un contenedor local registrado para Spaces, Sources y contexto compartido opcional relacionados. Puede estar en cualquier lugar y no necesita ser un repositorio Git. |
| **Space** | Un pseudoproyecto de colaboración con la IA para un propósito concreto dentro de una Instance. Define las reglas y capacidades para trabajar con un proyecto real y su documentación anexa. |
| **Source** | Un repositorio o directorio mantenido que proporciona capacidades de IA reutilizables. Pertenece a Core o a una Instance. |
| **Capability** | Una skill, agent o command reutilizable que se selecciona desde un Source sin copiarla. |
| **Definition** | La selección de capacidades independiente del cliente: `HARNESSIA.md` para Core o `SPACE.md` para un Space. |
| **Consumer** | Core o un Space cuando selecciona Capabilities desde Sources. |
| **Client Projection** | La configuración generada de OpenCode o Claude Code para un Consumer. |

Core, Instance y Space forman la jerarquía de contexto, no una estructura anidada de directorios:

```text
Core
└── Instance
    └── Space
```

El contexto se hereda en ese orden; las capas posteriores tienen mayor prioridad. El repositorio versiona el proyecto `Core/`, no las Instances locales. Las Instances se registran en `.harnessia/instances.yaml`, situado dentro de Core e ignorado por Git; solo se descubren las Instances registradas explícitamente. Core no incluye Instances instaladas ni vínculos a espacios de trabajo externos; los nombres y rutas que aparecen a continuación son ejemplos.

## Primeros pasos

Necesitas `make`, Git y [`uv`](https://docs.astral.sh/uv/). Las configuraciones generadas son compatibles con OpenCode 2.1.4 o posterior y Claude Code 2.1.220 o posterior. El comando interactivo de configuración de capacidades requiere además la CLI `opencode` y un terminal.

Desde la raíz del repositorio clonado, entra en `Core/` antes de ejecutar cualquier comando de Harnessia:

```sh
cd Core
```

El Makefile y la plantilla de configuración están dentro de `Core/`, no en la raíz del repositorio Git. No repitas `cd Core` si tu terminal ya está en ese directorio.

### Configuración rápida

Core incluye la plantilla comentada [`templates/space-setup.sh`](templates/space-setup.sh) para ejecutar el flujo completo. Cópiala al material de trabajo ignorado, edita los tres valores de configuración del inicio y ejecútala desde allí:

```sh
mkdir -p docs/wip
cp templates/space-setup.sh docs/wip/space-setup.sh
${EDITOR:-vi} docs/wip/space-setup.sh
bash docs/wip/space-setup.sh
```

La sección de configuración explica cada valor:

- `INSTANCE` es el nombre registrado y sensible a mayúsculas de la Instance, como `Work`.
- `INSTANCE_PATH` es su directorio absoluto, como `$HOME/Harnessia/Work`. La plantilla no proporciona deliberadamente ningún valor predeterminado para esta variable.
- `SPACE` es el ID en minúsculas del Space, como `atlas`.

El script es fail-closed y ejecuta esta secuencia:

- Si no existe el directorio de la Instance, `instance-create` crea su estructura mínima y la registra. Si el directorio ya existe, `instance-attach` lo valida y registra sin volver a crearlo. Un directorio existente debe ser ya una Instance válida.
- `sources-clone` instala los Sources fijados que falten para que el curador pueda considerar sus skills.
- Si no existe la ruta del Space, `space-create` lo crea y prepara. Un directorio regular sin `SPACE.md` se inicializa mediante `space-attach`, que añade solo los archivos Harnessia ausentes y conserva todo el contenido previo. Una ruta con un `SPACE.md` regular ya está inicializada y se omite su creación. Las demás colisiones se conservan y reportan.
- `space-configure` requiere la Instance registrada y el Space existente. Abre el curador, recomienda skills y servidores MCP según el objetivo, aplica solo una selección aprobada explícitamente y prepara las proyecciones de ambos clientes. Puede recomendar servidores que falten, pero nunca los instala ni autentica.
- `check` termina con una validación de solo lectura de la Instance objetivo.

`INSTANCE` y `SPACE` no son intercambiables: usa `INSTANCE=Work SPACE=atlas`, no al revés. Los nombres de Instance distinguen mayúsculas y minúsculas; los IDs de Space usan letras minúsculas, dígitos y guiones simples.

La plantilla también puede ejecutarse sin copiarla si se proporcionan todos los valores mediante el entorno:

```sh
INSTANCE=Work INSTANCE_PATH="$HOME/Harnessia/Work" SPACE=atlas \
  bash templates/space-setup.sh
```

Para usar un Space, abre directamente su directorio en OpenCode o Claude Code. Harnessia no proporciona ni necesita un launcher.

## Comandos habituales

| Qué quieres hacer | Comando |
| --- | --- |
| Preparar el proyecto Core para sesiones de mantenimiento de Harnessia | `make prepare-core` |
| Preparar un Space | `make prepare INSTANCE=<id> SPACE=<space-id>` |
| Preparar todos los Spaces de una Instance | `make prepare-instance INSTANCE=<id>` |
| Preparar Core y todos los Spaces registrados | `make prepare-all` |
| Crear y registrar una Instance | `make instance-create INSTANCE=<id> INSTANCE_PATH=<path>` |
| Conectar y registrar una Instance | `make instance-attach INSTANCE=<id> INSTANCE_PATH=<path>` |
| Crear y preparar un Space | `make space-create INSTANCE=<id> SPACE=<space-id>` |
| Conectar y preparar un directorio de Space existente | `make space-attach INSTANCE=<id> SPACE=<space-id>` |
| Configurar interactivamente las skills y selección MCP de un Space | `make space-configure INSTANCE=<id> SPACE=<space-id>` |
| Validar sin cambiar los archivos generados | `make check [INSTANCE=<id>]` |
| Listar las Instances registradas | `make instance-list` |
| Ejecutar los tests | `make test` |
| Ejecutar la verificación local completa y de solo lectura | `make verify` |

`make prepare-core` sirve específicamente para trabajar en el propio Harnessia. Lee la Core Definition de `HARNESSIA.md`, valida las skills de mantenimiento seleccionadas y genera la configuración de clientes de Core: enlaces relativos bajo `.opencode/skills/` y un único plugin de Claude bajo `.claude/skills/harnessia-core/`. No prepara ningún Space.

`make prepare INSTANCE=<id> SPACE=<space-id>` genera o actualiza la configuración de clientes de un Space existente. Resuelve las reglas heredadas de Core, su Instance y el propio Space, valida la selección de capacidades de `SPACE.md` y genera las proyecciones de OpenCode y Claude Code gestionadas por Harnessia para ese Space. No crea el Space, no modifica el proyecto real ni la documentación enlazados, no actualiza Sources y no inicia ningún cliente de IA.

`make space-create INSTANCE=<id> SPACE=<space-id>` crea un Space nuevo solo cuando no existe el directorio de destino. Escribe un `SPACE.md` mínimo, un `SOUL.md` mantenido vacío y un `INSTRUCTIONS.md` mínimo; después valida y prepara el Space. Si falla la creación o la preparación, Harnessia elimina la nueva estructura; nunca sobrescribe una ruta existente.

`make space-attach INSTANCE=<id> SPACE=<space-id>` inicializa un directorio regular existente que no contiene `SPACE.md`. Conserva todo el contenido existente, acepta los archivos regulares `SOUL.md` e `INSTRUCTIONS.md` que ya existan, crea solo los archivos mantenidos ausentes y prepara las proyecciones de ambos clientes. Cualquier colisión con un enlace simbólico o archivo mantenido no regular se rechaza antes de escribir. Si falla la preparación, Harnessia elimina únicamente los archivos añadidos durante la conexión.

`make space-configure INSTANCE=<id> SPACE=<space-id>` abre OpenCode Mini con el agente restringido `space-curator`. Harnessia proporciona un índice JSONL de skills válidas de Core y la Instance propietaria, un inventario saneado de nombres y estados MCP y la [guía MCP](docs/mcp-guide.md). El curador lee el objetivo, pregunta solo por el contexto que falta, recomienda una selección mínima con alternativas opcionales, descartadas y MCP útiles pendientes de instalación, y espera la aprobación explícita de las entradas `skills` y `mcp` exactas. No busca Sources externos de skills ni instala o autentica servidores MCP.

Cuando OpenCode Mini termina correctamente, Harnessia solo acepta cambios en `skills` y `mcp` del `SPACE.md` objetivo, valida la selección y prepara ambas proyecciones de cliente. Si no hay un cambio aprobado, no ejecuta la preparación. Una interrupción, una salida no cero del cliente, una selección inválida, cambios fuera de esos campos o un fallo de preparación restauran la Definition original y las proyecciones anteriores. Cada ejecución guarda `SPACE.before.md`, `skills.jsonl`, el inventario saneado `mcp-inventory.json` y, cuando corresponde, `SPACE.proposed.md` bajo `.harnessia/space-configure/<Instance>/<Space>/<run-id>/` dentro de Core, ignorado por Git. Si falla el inventario, la disponibilidad es desconocida, no una ausencia de servidores. Define `HARNESSIA_OPENCODE` solo cuando el ejecutable no sea el `opencode` disponible en `PATH`.

`INSTANCE` es el nombre registrado y sensible a mayúsculas de la Instance. Harnessia conserva su capitalización: una Instance registrada como `Work`, por ejemplo, se selecciona con `INSTANCE=Work`. Volver a adjuntar la misma ruta cambiando solo la capitalización migra un nombre antiguo en minúsculas.

Para la regeneración habitual de todo el sistema, usa `make prepare-all`; siempre valida Core y todos los Spaces registrados antes de reemplazar cualquier configuración generada para los clientes. Para regenerar solo los Spaces de una Instance, usa `make prepare-instance INSTANCE=<id>`. `make check` valida sin escribir y puede seguir usando `INSTANCE=<id>` para limitar su ámbito, mientras que `make verify` ejecuta los tests, las comprobaciones de Sources y la comprobación completa de solo lectura. La preparación no actualiza Sources, no cambia el contenido enlazado ni inicia ningún cliente de IA; solo `space-configure` abre OpenCode Mini para su sesión interactiva de curación explícita. Los logs se guardan en `logs/` dentro de Core, ignorado por Git.

## Mantenimiento de Sources

Core y cada Instance son propietarios de sus Sources. Los Sources Git reproducibles están fijados en el `SOURCES.yaml` de su propietario; también puede haber Sources locales sin versión, pero `sources-clone` no puede restaurarlos.

| Tarea | Comando |
| --- | --- |
| Clonar los Sources fijados que falten | `make sources-clone` |
| Validar los Sources y todo lo que los usa | `make sources-check` |
| Mostrar cambios locales y remotos conocidos | `make sources-status` |
| Actualizar los remotos sin cambiar los worktrees | `make sources-fetch` |
| Avanzar a las revisiones revisadas | `make sources-pull` |
| Validar, preparar y registrar las revisiones modificadas | `make sources-reconcile` |

El flujo de actualización es explícito:

```sh
make sources-fetch
make sources-status
make sources-pull
make sources-reconcile
make verify
```

`sources-pull` se detiene antes de cambiar nada si un Source tiene cambios, está en detached HEAD, ha divergido o no tiene upstream. Harnessia nunca resetea ni descarta trabajo de un Source.

Core selecciona `find-skills`, de Vercel, para buscar en el ecosistema y `skill-discovery`, de Codesigils, para inspeccionar candidatas con evidencias. Estas capacidades sirven para futuras conversaciones de mantenimiento; no amplían el curador `space-configure`, que sigue siendo exclusivamente local. Las [instrucciones del repositorio](AGENTS.md#skill-discovery) separan el discovery de la instalación y exigen que las incorporaciones aprobadas sigan el ciclo de Sources fijados. Instalar un Source no activa todas sus skills ni sus integraciones de plugin; cada Consumer selecciona únicamente las capacidades que declara.

Los Sources fijados de Core también incluyen `docker-skills`, de Docker, y `microsoft-playwright-cli`, de Microsoft, para flujos opcionales de contenedores y navegador. Cada Consumer selecciona sus capacidades exactas de forma independiente; clonar estos repositorios no instala Docker, el CLI de Playwright, navegadores ni dependencias, no arranca servicios ni autoriza limpiezas. La instalación y comprobación de compatibilidad del runtime siguen siendo operaciones separadas y explícitas.

## Qué contiene un Space

El [contrato de colaboración compartido](INSTRUCTIONS.md) adapta el rigor y la validación al desarrollo, investigación, consultoría, backlog o documentos. Prefiere los métodos Matt Pocock seleccionados que encajan, usa Caveman para un chat conciso, excluye Superpowers y exige que el usuario elija antes de añadir agentes, consulta especializada o worktrees. El curador recomienda Caveman y solo las skills Matt adecuadas al propósito; la selección requiere aprobación exacta y no se hereda automáticamente. Los Spaces nuevos empiezan con selecciones vacías hasta configurarlos.

El trabajo de varios pasos conserva un único checkpoint retomable al cerrar fases o interrumpirse, usando el registro de la tarea y la memoria local opcional y acotada. Registra progreso verificado, decisiones, comprobaciones, bloqueos y siguiente acción, no conversaciones ni preferencias aprendidas. Las instrucciones y guías mantenidas de Harnessia están en inglés salvo esta guía; se conservan evidencias históricas, textos de terceros e idiomas solicitados para entregables. `caveman-compress` no es una operación por defecto.

Un Space no es el proyecto real. Es el pseudoproyecto que abres en el cliente de IA para mantener las reglas de colaboración controladas y separadas del contenido de trabajo. Dentro, `SOUL.md` registra preferencias explícitas y duraderas sobre el estilo y criterio de colaboración, `INSTRUCTIONS.md` define las reglas operativas, `SPACE.md` selecciona capacidades desde `core/<source-id>` e `instance/<source-id>`, y los enlaces opcionales `project` y `documentation` conectan el proyecto real y su documentación anexa.

Harnessia resuelve el contexto activo de menor a mayor prioridad: SOUL de Core, SOUL opcional de la Instance, SOUL del Space, instrucciones de Core, instrucciones opcionales de la Instance, instrucciones del Space y memoria opcional del Space. Las capas posteriores especializan el comportamiento local; el contrato compartido prohíbe debilitar silenciosamente las reglas de seguridad y aprobación, y las skills o la memoria no amplían permisos. Es un contrato de instrucciones, no una resolución semántica determinista de conflictos ni una sandbox de ejecución. El SOUL de un Space es un archivo regular mantenido que puede empezar vacío; Harnessia nunca lo reescribe y un cliente de IA solo debe actualizarlo cuando el usuario solicite explícitamente una preferencia duradera.

`INDEX.md`, `SPACE.md`, los README y la documentación siguen siendo navegación, definiciones o material de consulta; Harnessia no activa cada archivo Markdown como instrucción. Core ejecuta la orquestación y genera paths relativos para cada cliente, por lo que Core y las Instances pueden vivir en ubicaciones no relacionadas del sistema de archivos.

OpenCode admite skills, agents, commands y listas permitidas de MCP. Claude Code admite las instrucciones y skills compartidas; los agents y commands de OpenCode no se traducen. La configuración de proyecto de Claude bloquea las herramientas MCP, pero para aislar también los servidores MCP heredados hay que iniciar Claude desde el Space con:

```sh
claude --setting-sources project --strict-mcp-config --mcp-config .claude/harnessia-mcp.json
```

Las conexiones MCP se configuran una sola vez en la configuración de usuario o administrada de OpenCode; cada Space selecciona explícitamente sus IDs bajo `mcp` en `SPACE.md`. El curador utiliza un inventario saneado de nombres y estados y la [guía de selección MCP](docs/mcp-guide.md), incluyendo recomendaciones de servidores aún no configurados. Los cambios manuales requieren `make prepare INSTANCE=<id> SPACE=<space-id>`. Claude siempre recibe un catálogo MCP vacío, incluso con una selección no vacía en OpenCode: no se añade ningún servidor dummy ni esquema de herramientas MCP.

El proyecto y la documentación enlazados siguen siendo contenido de trabajo externo. Harnessia valida sus límites, pero no los inspecciona ni trata sus archivos como instrucciones o capacidades.

## Documentación

- [Índice de documentación](docs/INDEX.md)
- [Arquitectura actual](docs/DESIGN.md)
- [Core Definition](docs/core-definition.md)
- [Space Definition](docs/space-definition.md)
- [Glosario](docs/GLOSSARY.md)
- [Registro fechado de implementación y mantenimiento](docs/PROJECT.md)

## Licencia

Copyright (c) 2026 Samuel Vicent. Harnessia Core se distribuye bajo la [Licencia Pública General de GNU, únicamente la versión 3](LICENSE) (`GPL-3.0-only`), sin garantía. El texto completo de la licencia está en `Core/LICENSE`. Las Sources de terceros conservan sus propias licencias; la licencia de Core no cambia la de su contenido.
