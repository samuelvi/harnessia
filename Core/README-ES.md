# Harnessia Core

[English](README.md)

Harnessia crea Spaces para colaborar con la IA. Cada Space mantiene sus reglas y capacidades separadas de los proyectos y la documentación con los que trabaja. Tú eliges lo que necesita cada Space; Harnessia valida la selección y genera la configuración para OpenCode y Claude Code.

Las capacidades permanecen en sus Sources originales. Harnessia las enlaza en lugar de copiarlas o reescribirlas.

**Todo el proyecto Harnessia Core está en `Core/`, incluidas estas guías operativas y la licencia.** Git está un nivel por encima. Solo se versionan `Core/` y el `.gitignore` raíz; cualquier otra carpeta hermana queda excluida por defecto. Salvo indicación contraria, todas las rutas y comandos de esta guía son relativos a `Core/`, no a la raíz del repositorio Git.

`Core/docs/` contiene tanto referencias mantenidas del producto como material de trabajo local. Los archivos de referencia y `docs/adr/` se versionan; las entradas privadas, los resultados locales revisados y el trabajo en curso corresponden, respectivamente, a `docs/sources/`, `docs/deliverables/` y `docs/wip/`. **`Core/.gitignore` excluye esos tres subdirectorios; su contenido nunca se publica.** La configuración del IDE corresponde a `Core/.idea/`, ignorado. Los repositorios de capacidades y las proyecciones de clientes generadas también permanecen en Core.

## Conceptos de un vistazo

| Concepto | Significado |
| --- | --- |
| **Core** | El proyecto central de Harnessia dentro de `Core/`. Contiene el motor, el contexto compartido, los Sources compartidos y la documentación. |
| **Instance** | Contenedor local para Spaces y Sources relacionados, con configuración y contexto compartidos opcionales. Puede estar en cualquier lugar y no necesita ser un repositorio Git. |
| **Space** | Entorno de colaboración con la IA para un propósito concreto dentro de una Instance. Ábrelo directamente en el cliente de IA. |
| **Project Workspace** | Directorio opcional dentro de un Space para un proyecto o iniciativa, por ejemplo `work/<project-id>/`. |
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

El contexto se hereda en ese orden; las capas posteriores tienen mayor prioridad. El repositorio versiona `Core/`, no las Instances locales. Una Instance puede existir sin estar registrada. La CLI solo descubre Instances a través del registro `.harnessia/instances.yaml`, situado dentro de Core e ignorado por Git. Core se distribuye sin Instances ni enlaces de trabajo locales; los nombres y rutas siguientes son ejemplos.

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

- `INSTANCE` es el nombre de la Instance y distingue mayúsculas de minúsculas. La plantilla usa `Default` si no se indica otro nombre; el motor no le da un significado especial.
- `INSTANCE_PATH` es el directorio absoluto de la Instance. Indícalo expresamente; la plantilla no tiene una ruta predeterminada.
- `SPACE` es el ID en minúsculas del Space. La plantilla usa `atlas` si no se indica otro.

El script es fail-closed y ejecuta esta secuencia:

- Si no existe el directorio de la Instance, `instance-create` crea su estructura mínima y la registra. Si el directorio ya existe, `instance-attach` lo valida y registra sin volver a crearlo. Un directorio existente debe ser ya una Instance válida.
- `sources-clone INSTANCE=<id>` instala los Sources fijados que falten en Core y en la Instance elegida para que el curador pueda considerar sus skills.
- Si no existe la ruta del Space, `space-create` lo crea y prepara. Un directorio regular sin `SPACE.md` se inicializa mediante `space-attach`, que añade solo los archivos Harnessia ausentes y conserva todo el contenido previo. Una ruta con un `SPACE.md` regular ya está inicializada y se omite su creación. Las demás colisiones se conservan y reportan.
- `space-configure` requiere la Instance registrada y el Space existente. Abre el curador, recomienda skills y servidores MCP según el objetivo, aplica solo una selección aprobada explícitamente y prepara las proyecciones de ambos clientes. Puede recomendar servidores que falten, pero nunca los instala ni autentica.
- `check` termina con una validación de solo lectura de la Instance objetivo.

`INSTANCE` nombra el contenedor; `SPACE` nombra un Space dentro de él. Los IDs de Space usan letras minúsculas, dígitos y guiones simples.

La plantilla también puede ejecutarse sin copiarla si se proporcionan todos los valores mediante el entorno:

```sh
INSTANCE=Default INSTANCE_PATH="$HOME/Harnessia/Default" SPACE=atlas \
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

`make prepare INSTANCE=<id> SPACE=<space-id>` resuelve el contexto activo y valida la selección de capacidades de `SPACE.md` antes de generar las proyecciones de ambos clientes para un Space existente. No crea el Space, no modifica contenido enlazado, no actualiza Sources y no inicia ningún cliente de IA.

`make space-create INSTANCE=<id> SPACE=<space-id>` crea un Space nuevo solo cuando no existe el directorio de destino. Escribe un `SPACE.md` mínimo, un `SOUL.md` mantenido vacío y un `INSTRUCTIONS.md` mínimo; después valida y prepara el Space. Si falla la creación o la preparación, Harnessia elimina la nueva estructura; nunca sobrescribe una ruta existente.

`make space-attach INSTANCE=<id> SPACE=<space-id>` inicializa un directorio regular existente que no contiene `SPACE.md`. Conserva todo el contenido existente, acepta los archivos regulares `SOUL.md` e `INSTRUCTIONS.md` que ya existan, crea solo los archivos mantenidos ausentes y prepara las proyecciones de ambos clientes. Cualquier colisión con un enlace simbólico o archivo mantenido no regular se rechaza antes de escribir. Si falla la preparación, Harnessia elimina únicamente los archivos añadidos durante la conexión.

`make space-configure INSTANCE=<id> SPACE=<space-id>` abre OpenCode Mini con el agente restringido `space-curator`. Harnessia proporciona un índice JSONL de skills válidas de Core y la Instance propietaria, un inventario saneado de nombres y estados MCP y la [guía MCP](docs/mcp-guide.md). El curador lee el objetivo, pregunta solo por el contexto que falta, recomienda una selección mínima con alternativas opcionales, descartadas y MCP útiles pendientes de instalación, y espera la aprobación explícita de las entradas `skills` y `mcp` exactas. No busca Sources externos de skills ni instala o autentica servidores MCP.

Cuando OpenCode Mini termina correctamente, Harnessia solo acepta cambios en `skills` y `mcp` del `SPACE.md` objetivo, valida la selección y prepara ambas proyecciones de cliente. Si no hay un cambio aprobado, no ejecuta la preparación. Una interrupción, una salida no cero del cliente, una selección inválida, cambios fuera de esos campos o un fallo de preparación restauran la Definition original y las proyecciones anteriores. Cada ejecución guarda `SPACE.before.md`, `skills.jsonl`, el inventario saneado `mcp-inventory.json` y, cuando corresponde, `SPACE.proposed.md` bajo `.harnessia/space-configure/<Instance>/<Space>/<run-id>/` dentro de Core, ignorado por Git. Si falla el inventario, la disponibilidad es desconocida, no una ausencia de servidores. Define `HARNESSIA_OPENCODE` solo cuando el ejecutable no sea el `opencode` disponible en `PATH`.

`INSTANCE` debe respetar las mayúsculas y minúsculas del registro. Volver a adjuntar la misma ruta con un cambio solo de mayúsculas y minúsculas actualiza el nombre registrado.

Para la regeneración habitual de todo el sistema, usa `make prepare-all`; siempre valida Core y todos los Spaces registrados antes de reemplazar cualquier configuración generada para los clientes. Para regenerar solo los Spaces de una Instance, usa `make prepare-instance INSTANCE=<id>`. `make check` valida sin escribir y puede seguir usando `INSTANCE=<id>` para limitar su ámbito, mientras que `make verify` ejecuta los tests, las comprobaciones de Sources y la comprobación completa de solo lectura. La preparación no actualiza Sources, no cambia el contenido enlazado ni inicia ningún cliente de IA; solo `space-configure` abre OpenCode Mini para su sesión interactiva de curación explícita. Los logs se guardan en `logs/` dentro de Core, ignorado por Git.

## Mantenimiento de Sources

Core y cada Instance son propietarios de sus Sources. Los Sources Git reproducibles están fijados en el `SOURCES.yaml` de su propietario; también puede haber Sources locales sin versión, pero `sources-clone` no puede restaurarlos.

| Tarea | Comando |
| --- | --- |
| Clonar los Sources fijados que falten | `make sources-clone [INSTANCE=<id>]` |
| Validar los Sources y todo lo que los usa | `make sources-check` |
| Mostrar cambios locales y remotos conocidos | `make sources-status` |
| Actualizar los remotos sin cambiar los worktrees | `make sources-fetch` |
| Avanzar a las revisiones revisadas | `make sources-pull` |
| Validar, preparar y registrar las revisiones modificadas | `make sources-reconcile` |

Con `INSTANCE=<id>`, la clonación se limita a Core y a esa Instance registrada. Sin ese parámetro, incluye todas las Instances registradas. Los demás comandos de Sources operan sobre todos los propietarios registrados.

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

El Source `googlechrome-modern-web-guidance`, de Google Chrome, proporciona `skills/modern-web-guidance` para HTML, CSS, APIs del navegador, accesibilidad y compatibilidad modernos. Cada Consumer lo selecciona de forma independiente. Sus guías locales siguen la revisión fijada del Source; su CLI npm no, y descargar o ejecutar un runtime revisado requiere aprobación separada.

## Qué contiene un Space

Cada Instance puede mantener sus reglas de colaboración en su propio `INSTRUCTIONS.md`. Solo los Spaces de esa Instance las heredan. El curador lee esas reglas cuando existen; las selecciones de skills y MCP siguen requiriendo aprobación exacta. Los Spaces nuevos empiezan con selecciones vacías hasta configurarlos.

Un Space es independiente de los proyectos con los que trabaja. `SOUL.md` registra preferencias explícitas y duraderas de colaboración, `INSTRUCTIONS.md` define las reglas operativas y `SPACE.md` selecciona capacidades desde `core/<source-id>` e `instance/<source-id>`. Los [enlaces de trabajo](docs/space-definition.md#working-links) opcionales conectan proyectos y documentación externos.

Harnessia resuelve el contexto activo de menor a mayor prioridad: SOUL de Core, SOUL opcional de la Instance, SOUL del Space, instrucciones opcionales de la Instance, instrucciones del Space y memoria opcional del Space. Los Spaces no heredan las reglas de mantenimiento de Core en `AGENTS.md`. El orden no resuelve conflictos semánticos ni impone permisos en tiempo de ejecución. El SOUL de un Space es un archivo regular mantenido que puede empezar vacío; Harnessia nunca lo reescribe y un cliente de IA solo debe actualizarlo cuando el usuario solicite explícitamente una preferencia duradera.

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

## Créditos

Canción de inspiración: [Amnesia — Ibiza (1988)](https://www.youtube.com/watch?v=KSjLGw9CbGE&list=RDKSjLGw9CbGE)
