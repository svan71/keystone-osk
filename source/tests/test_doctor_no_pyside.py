import subprocess
import sys
import textwrap


def test_doctor_report_imports_and_reports_without_pyside6() -> None:
    code = textwrap.dedent(
        """
        import importlib.abc

        class Block(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path, target=None):
                if name == "PySide6" or name.startswith("PySide6."):
                    raise ImportError("PySide6 blocked")
                return None

        import sys
        sys.meta_path.insert(0, Block())

        from keystone_osk.doctor import doctor_report

        report = doctor_report(
            {"XDG_STATE_HOME": "/tmp/keystone-doctor-no-pyside-state"},
            command_sender=lambda *args, **kwargs: None,
            process_running=lambda: False,
            which=lambda name: None,
            uinput_checker=lambda: ("OK", "/dev/uinput writable"),
            tray_checker=lambda: "unknown (PySide6 unavailable)",
        )
        assert "INFO pyside6: not installed" in report, report
        """
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stdout + result.stderr
