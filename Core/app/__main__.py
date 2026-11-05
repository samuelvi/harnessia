from argparse import ArgumentParser
from pathlib import Path
import sys

from .check import check_all, check_instance, render_all_check, render_instance_check
from .instances import (
    load_instance_registry,
    registered_instance,
    render_instance_registry,
)
from .instance_lifecycle import attach_instance, create_instance
from .layout import CoreLayout
from .prepare import (
    prepare_all,
    prepare_core,
    prepare_instance,
    prepare_instance_all,
)
from .source_bootstrap import (
    check_sources,
    clone_sources,
    reconcile_sources,
    render_check_result,
    render_clone_result,
    render_reconcile_result,
)
from .source_status import inspect_sources, render_source_status
from .source_update import (
    fetch_sources,
    pull_sources,
    render_fetch_result,
    render_pull_result,
)
from .space import HarnessiaError
from .space_assistant import configure_space
from .space_lifecycle import attach_space, create_space


def main(argv: list[str] | None = None, directory: Path | None = None) -> int:
    parser = ArgumentParser(prog="harnessia")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--space", required=True)
    prepare_parser.add_argument("--instance", required=True)
    subparsers.add_parser("prepare-core")
    prepare_instance_parser = subparsers.add_parser("prepare-instance")
    prepare_instance_parser.add_argument("id")
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--instance")
    subparsers.add_parser("prepare-all")
    instance_parser = subparsers.add_parser("instance")
    instance_subparsers = instance_parser.add_subparsers(
        dest="instance_command", required=True
    )
    create_parser = instance_subparsers.add_parser("create")
    create_parser.add_argument("id")
    create_parser.add_argument("path")
    attach_parser = instance_subparsers.add_parser("attach")
    attach_parser.add_argument("id")
    attach_parser.add_argument("path")
    instance_subparsers.add_parser("list")
    space_parser = subparsers.add_parser("space")
    space_subparsers = space_parser.add_subparsers(
        dest="space_command", required=True
    )
    create_space_parser = space_subparsers.add_parser("create")
    create_space_parser.add_argument("instance")
    create_space_parser.add_argument("id")
    attach_space_parser = space_subparsers.add_parser("attach")
    attach_space_parser.add_argument("instance")
    attach_space_parser.add_argument("id")
    configure_space_parser = space_subparsers.add_parser("configure")
    configure_space_parser.add_argument("instance")
    configure_space_parser.add_argument("id")
    subparsers.add_parser("sources-clone")
    subparsers.add_parser("sources-check")
    subparsers.add_parser("sources-status")
    subparsers.add_parser("sources-fetch")
    subparsers.add_parser("sources-pull")
    subparsers.add_parser("sources-reconcile")
    arguments = parser.parse_args(argv)

    directory = (directory or Path(__file__).resolve().parents[1]).resolve()
    core = CoreLayout.at(directory)
    try:
        if arguments.command == "prepare":
            registered = registered_instance(core, arguments.instance)
            if registered.state != "available":
                raise HarnessiaError(
                    f"Instance '{registered.id}' is {registered.state}: "
                    f"{registered.path}"
                )
            prepare_instance(core, registered.layout, arguments.space)
            return 0
        if arguments.command == "prepare-core":
            prepare_core(directory)
            return 0
        if arguments.command == "check":
            if arguments.instance:
                registered = registered_instance(core, arguments.instance)
                if registered.state != "available":
                    raise HarnessiaError(
                        f"Instance '{registered.id}' is {registered.state}: "
                        f"{registered.path}"
                    )
                print(render_instance_check(check_instance(core, registered.layout)))
                return 0
            print(render_all_check(check_all(core)))
            return 0
        if arguments.command == "prepare-instance":
            registered = registered_instance(core, arguments.id)
            if registered.state != "available":
                raise HarnessiaError(
                    f"Instance '{registered.id}' is {registered.state}: "
                    f"{registered.path}"
                )
            results = prepare_instance_all(core, registered.layout)
            print(f"Prepared {len(results)} Spaces in Instance {registered.id}.")
            return 0
        if arguments.command == "prepare-all":
            results = prepare_all(directory)
            print(f"Prepared Core and {len(results.spaces)} Spaces.")
            return 0
        if arguments.command == "instance":
            if arguments.instance_command == "create":
                result = create_instance(
                    core, arguments.id, Path(arguments.path).expanduser().resolve()
                )
                print(f"Created and attached Instance {result.instance.id} at {result.instance.path}.")
                return 0
            if arguments.instance_command == "attach":
                result = attach_instance(
                    core, arguments.id, Path(arguments.path).expanduser().resolve()
                )
                print(
                    f"Attached Instance {result.instance.id} at {result.instance.path}; "
                    f"initialized {len(result.initialized_souls)} Space SOUL files."
                )
                return 0
            if arguments.instance_command == "list":
                print(render_instance_registry(load_instance_registry(core)))
                return 0
        if arguments.command == "space":
            if arguments.space_command == "create":
                registered = registered_instance(core, arguments.instance)
                if registered.state != "available":
                    raise HarnessiaError(
                        f"Instance '{registered.id}' is {registered.state}: "
                        f"{registered.path}"
                    )
                result = create_space(core, registered.layout, arguments.id)
                print(
                    f"Created and prepared Space {registered.id}/{arguments.id} "
                    f"at {result.directory}."
                )
                return 0
            if arguments.space_command == "attach":
                registered = registered_instance(core, arguments.instance)
                if registered.state != "available":
                    raise HarnessiaError(
                        f"Instance '{registered.id}' is {registered.state}: "
                        f"{registered.path}"
                    )
                result = attach_space(core, registered.layout, arguments.id)
                print(
                    f"Attached and prepared Space {registered.id}/{arguments.id} "
                    f"at {result.directory}; initialized "
                    f"{len(result.initialized_files)} maintained files."
                )
                return 0
            if arguments.space_command == "configure":
                registered = registered_instance(core, arguments.instance)
                if registered.state != "available":
                    raise HarnessiaError(
                        f"Instance '{registered.id}' is {registered.state}: "
                        f"{registered.path}"
                    )
                result = configure_space(core, registered.layout, arguments.id)
                if result.changed:
                    print(
                        f"Configured and prepared Space "
                        f"{registered.id}/{arguments.id}."
                    )
                else:
                    print(
                        f"No approved skill changes for Space "
                        f"{registered.id}/{arguments.id}."
                    )
                return 0
        if arguments.command == "sources-clone":
            print(render_clone_result(clone_sources(directory)))
            return 0
        if arguments.command == "sources-check":
            print(render_check_result(check_sources(directory)))
            return 0
        if arguments.command == "sources-status":
            print(render_source_status(inspect_sources(directory)))
            return 0
        if arguments.command == "sources-fetch":
            print(render_fetch_result(fetch_sources(directory)))
            return 0
        if arguments.command == "sources-pull":
            print(render_pull_result(pull_sources(directory)))
            return 0
        if arguments.command == "sources-reconcile":
            print(render_reconcile_result(reconcile_sources(directory)))
            return 0
    except HarnessiaError as error:
        if arguments.command not in {"prepare", "prepare-core"}:
            print(f"ERROR {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
