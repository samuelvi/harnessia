from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.instances import (
    consumer_instance_layouts,
    load_instance_registry,
    register_instance,
    registered_instance,
    render_instance_registry,
)
from app.layout import CoreLayout
from app.space import HarnessiaError


class InstanceRegistryTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.core = CoreLayout.at(self.root / "core")
        self.core.directory.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_registry_is_empty(self):
        self.assertEqual(load_instance_registry(self.core), ())
        self.assertEqual(render_instance_registry(()), "No Instances registered.")

    def test_registers_missing_path_and_reports_state(self):
        target = self.root / "instances/work"

        registered = register_instance(self.core, "work", target)
        loaded = load_instance_registry(self.core)

        self.assertEqual(loaded, (registered,))
        self.assertEqual(registered.state, "missing")
        self.assertIn("work | missing", render_instance_registry(loaded))
        self.assertTrue((self.core.directory / ".harnessia/instances.yaml").is_file())
        self.assertFalse((self.root / ".harnessia").exists())

    def test_reports_available_and_invalid_instances(self):
        available = self.root / "instances/available"
        available.joinpath("spaces").mkdir(parents=True)
        invalid = self.root / "instances/invalid"
        invalid.mkdir(parents=True)
        register_instance(self.core, "available", available)
        register_instance(self.core, "invalid", invalid)

        instances = load_instance_registry(self.core)

        self.assertEqual(
            {instance.id: instance.state for instance in instances},
            {"available": "available", "invalid": "invalid"},
        )

    def test_registration_updates_path_for_existing_id(self):
        first = self.root / "instances/first"
        second = self.root / "instances/second"
        register_instance(self.core, "work", first)

        register_instance(self.core, "work", second)

        self.assertEqual(registered_instance(self.core, "work").path, second)

    def test_rejects_two_ids_for_same_path(self):
        target = self.root / "instances/shared"
        register_instance(self.core, "work", target)

        with self.assertRaisesRegex(HarnessiaError, "already registered as 'work'"):
            register_instance(self.core, "sandbox", target)

    def test_rejects_relative_registration_path(self):
        with self.assertRaisesRegex(HarnessiaError, "path must be absolute"):
            register_instance(self.core, "work", Path("relative"))

    def test_rejects_unknown_registry_fields(self):
        registry = self.core.directory / ".harnessia/instances.yaml"
        registry.parent.mkdir()
        registry.write_text("version: 1\ninstances: []\nextra: true\n")

        with self.assertRaisesRegex(HarnessiaError, "unsupported field 'extra'"):
            load_instance_registry(self.core)

    def test_consumer_layouts_include_only_registered_instances(self):
        external = self.root / "instances/sandbox"
        external.joinpath("spaces").mkdir(parents=True)
        register_instance(self.core, "sandbox", external)

        layouts = consumer_instance_layouts(self.core)

        self.assertEqual(tuple(layout.id for layout in layouts), ("sandbox",))
        self.assertEqual(layouts[0].spaces, external / "spaces")

    def test_unavailable_registered_instance_blocks_consumer_discovery(self):
        register_instance(self.core, "work", self.root / "missing")

        with self.assertRaisesRegex(HarnessiaError, "work: missing"):
            consumer_instance_layouts(self.core)


if __name__ == "__main__":
    unittest.main()
