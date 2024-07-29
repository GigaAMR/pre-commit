from __future__ import annotations

import contextlib
import os.path
from collections.abc import Generator
from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.errors import FatalError
from pre_commit.parse_shebang import find_executable
from pre_commit.prefix import Prefix

ENVIRONMENT_DIR = 'coursier'

get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
run_hook = lang_base.basic_run_hook


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    lang_base.assert_version_default('coursier', version)

    # Support both possible executable names (either "cs" or "coursier")
    cs = find_executable('cs') or find_executable('coursier')
    if cs is None:
        raise AssertionError(
            'pre-commit requires system-installed "cs" or "coursier" '
            'executables in the application search path',
        )

    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)

    def _install(*opts: str) -> None:
        assert cs is not None
        lang_base.setup_cmd(prefix, (cs, 'fetch', *opts))
        lang_base.setup_cmd(prefix, (cs, 'install', '--dir', envdir, *opts))

    with in_env(prefix, version):
        channel = prefix.path('.pre-commit-channel')
        if os.path.isdir(channel):
            for app_descriptor in os.listdir(channel):
                _, app_file = os.path.split(app_descriptor)
                app, _ = os.path.splitext(app_file)
                _install(
                    '--default-channels=false',
                    '--channel', channel,
                    app,
                )
        elif not additional_dependencies:
            raise FatalError(
                'expected .pre-commit-channel dir or additional_dependencies',
            )

        if additional_dependencies:
            _install(*additional_dependencies)


def get_env_patch(target_dir: str) -> PatchesT:
    return (
        ('PATH', (target_dir, os.pathsep, Var('PATH'))),
        ('COURSIER_CACHE', os.path.join(target_dir, '.cs-cache')),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield
