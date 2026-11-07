#!/usr/bin/env bash

# Harnessia Instance and Space setup template.
#
# Copy this file to Core/docs/wip/, adjust the three values below and run it with
# Bash. You can also override any value through the environment, for example:
#
#   INSTANCE=Work INSTANCE_PATH="$HOME/Harnessia/Work" SPACE=atlas \
#     bash templates/space-setup.sh

set -Eeuo pipefail

# INSTANCE is the registered, case-sensitive Instance name.
# Examples: Work, Customer-A.
INSTANCE="${INSTANCE:-Work}"

# INSTANCE_PATH is the absolute directory that contains the Instance.
# It has no default: set it to a real location on this machine. An existing
# directory must already contain a valid Harnessia Instance.
INSTANCE_PATH="${INSTANCE_PATH:-}"

# SPACE is the lowercase Space ID inside INSTANCE_PATH/spaces/.
# It may contain digits and single hyphens, for example: atlas or api-v2.
SPACE="${SPACE:-atlas}"

# Resolve Core from Core/templates/ or a copy directly under Core/docs/wip/.
# Never use the caller's working directory to choose the project.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../Makefile" && -f "$SCRIPT_DIR/../HARNESSIA.md" ]]; then
  CORE_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
elif [[ -f "$SCRIPT_DIR/../../Makefile" &&
        -f "$SCRIPT_DIR/../../HARNESSIA.md" ]]; then
  CORE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
else
  printf 'ERROR: run the template from Core/templates/ or Core/docs/wip/.\n' >&2
  exit 2
fi
cd "$CORE_DIR"

# Refuse empty, relative and former documentation-placeholder paths before
# changing anything or invoking Make.
if [[ -z "$INSTANCE_PATH" ||
      "$INSTANCE_PATH" == /absolute/path/* ||
      "$INSTANCE_PATH" == /Users/me/* ||
      "$INSTANCE_PATH" != /* ]]; then
  printf 'ERROR: set INSTANCE_PATH to the absolute Instance directory.\n' >&2
  exit 2
fi

# Create and register a missing Instance. If its directory already exists,
# validate and register it without recreating or overwriting it.
if [[ -d "$INSTANCE_PATH" ]]; then
  make instance-attach INSTANCE="$INSTANCE" INSTANCE_PATH="$INSTANCE_PATH"
elif [[ -e "$INSTANCE_PATH" || -L "$INSTANCE_PATH" ]]; then
  printf 'ERROR: Instance path exists but is not a regular directory: %s\n' \
    "$INSTANCE_PATH" >&2
  exit 2
else
  make instance-create INSTANCE="$INSTANCE" INSTANCE_PATH="$INSTANCE_PATH"
fi

# Install every missing pinned Source so the skill curator sees the complete
# local catalog. Existing Source directories are never replaced.
make sources-clone

SPACE_PATH="$INSTANCE_PATH/spaces/$SPACE"

# Create a Space at an absent path. Attach an existing regular directory by
# adding only missing Harnessia files; all prior content remains untouched.
if [[ -f "$SPACE_PATH/SPACE.md" && ! -L "$SPACE_PATH/SPACE.md" ]]; then
  printf 'Space already exists; skipping creation: %s\n' "$SPACE_PATH"
elif [[ -d "$SPACE_PATH" && ! -L "$SPACE_PATH" ]]; then
  make space-attach INSTANCE="$INSTANCE" SPACE="$SPACE"
elif [[ -e "$SPACE_PATH" || -L "$SPACE_PATH" ]]; then
  printf 'ERROR: Space path exists but is not a regular directory: %s\n' \
    "$SPACE_PATH" >&2
  exit 2
else
  make space-create INSTANCE="$INSTANCE" SPACE="$SPACE"
fi

# Open the restricted OpenCode Mini curator. It proposes local skills and MCP
# access, including installation gaps, but never installs or authenticates MCPs.
# It edits SPACE.md only after approval; Harnessia prepares both client outputs.
make space-configure INSTANCE="$INSTANCE" SPACE="$SPACE"

# Finish with a read-only validation of the target Instance and all its Spaces.
make check INSTANCE="$INSTANCE"
