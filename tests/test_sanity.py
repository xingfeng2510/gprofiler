#
# Copyright (c) Granulate. All rights reserved.
# Licensed under the AGPL3 License. See LICENSE.md in the project root for license information.
#
from pathlib import Path
from threading import Event
from typing import Any, Callable, List, Optional

import pytest
from docker import DockerClient
from docker.models.images import Image

from gprofiler.merge import parse_one_collapsed
from gprofiler.profilers.perf import SystemProfiler
from gprofiler.profilers.php import PHPSpyProfiler
from gprofiler.profilers.python import PySpyProfiler, PythonEbpfProfiler
from gprofiler.profilers.ruby import RbSpyProfiler
from tests import PHPSPY_DURATION
from tests.conftest import AssertInCollapsed
from tests.utils import (
    RUNTIME_PROFILERS,
    assert_function_in_collapsed,
    make_java_profiler,
    run_gprofiler_in_container_for_one_session,
    snapshot_one_collaped,
)


@pytest.mark.parametrize("runtime", ["java"])
def test_java_from_host(
    tmp_path: Path,
    application_pid: int,
    assert_application_name: Callable,
    assert_collapsed: AssertInCollapsed,
) -> None:
    with make_java_profiler(
        frequency=99,
        storage_dir=str(tmp_path),
        java_async_profiler_mode="itimer",
    ) as profiler:
        _ = assert_application_name  # Required for mypy unused argument warning
        process_collapsed = snapshot_one_collaped(profiler)
        assert_collapsed(process_collapsed)


@pytest.mark.parametrize("runtime", ["python"])
def test_pyspy(
    tmp_path: Path,
    application_pid: int,
    assert_collapsed: AssertInCollapsed,
    assert_application_name: Callable,
    python_version: Optional[str],
) -> None:
    _ = assert_application_name  # Required for mypy unused argument warning
    with PySpyProfiler(1000, 3, Event(), str(tmp_path), add_versions=True) as profiler:
        # not using snapshot_one_collaped because there are multiple Python processes running usually.
        process_collapsed = profiler.snapshot()[application_pid]
        assert_collapsed(process_collapsed)
        assert_function_in_collapsed("PyYAML==6.0", process_collapsed)  # Ensure package info is presented
        # Ensure Python version is presented
        assert python_version is not None, "Failed to find python version"
        assert_function_in_collapsed(f"standard-library=={python_version}", process_collapsed)


@pytest.mark.parametrize("runtime", ["php"])
def test_phpspy(
    tmp_path: Path,
    application_pid: int,
    assert_collapsed: AssertInCollapsed,
) -> None:
    with PHPSpyProfiler(
        1000, PHPSPY_DURATION, Event(), str(tmp_path), php_process_filter="php", php_mode="phpspy"
    ) as profiler:
        process_collapsed = profiler.snapshot()[application_pid]
        assert_collapsed(process_collapsed)


@pytest.mark.parametrize("runtime", ["ruby"])
def test_rbspy(
    tmp_path: Path,
    application_pid: int,
    assert_collapsed: AssertInCollapsed,
    gprofiler_docker_image: Image,
) -> None:
    with RbSpyProfiler(1000, 3, Event(), str(tmp_path), "rbspy") as profiler:
        process_collapsed = snapshot_one_collaped(profiler)
        assert_collapsed(process_collapsed)


@pytest.mark.parametrize("runtime", ["nodejs"])
def test_nodejs(
    tmp_path: Path,
    application_pid: int,
    assert_collapsed: AssertInCollapsed,
    gprofiler_docker_image: Image,
) -> None:
    with SystemProfiler(
        1000, 6, Event(), str(tmp_path), perf_mode="fp", perf_inject=True, perf_dwarf_stack_size=0
    ) as profiler:
        process_collapsed = profiler.snapshot()[application_pid]
        assert_collapsed(process_collapsed)


@pytest.mark.parametrize("runtime", ["python"])
def test_python_ebpf(
    tmp_path: Path,
    application_pid: int,
    assert_collapsed: AssertInCollapsed,
    assert_application_name: Callable,
    gprofiler_docker_image: Image,
    python_version: Optional[str],
    no_kernel_headers: Any,
) -> None:
    _ = assert_application_name  # Required for mypy unused argument warning
    with PythonEbpfProfiler(1000, 5, Event(), str(tmp_path), add_versions=True) as profiler:
        try:
            collapsed = profiler.snapshot()
        except UnicodeDecodeError as e:
            print(repr(e.object))  # print the faulty binary data
            raise
        process_collapsed = collapsed[application_pid]
        assert_collapsed(process_collapsed)
        assert_function_in_collapsed("do_syscall_64_[k]", process_collapsed)  # ensure kernels stacks exist
        assert_function_in_collapsed(
            "_PyEval_EvalFrameDefault_[pn]", process_collapsed
        )  # ensure native user stacks exist
        # ensure class name exists for instance methods
        assert_function_in_collapsed("lister.Burner.burner", process_collapsed)
        # ensure class name exists for class methods
        assert_function_in_collapsed("lister.Lister.lister", process_collapsed)
        assert_function_in_collapsed("PyYAML==6.0", process_collapsed)  # ensure package info exists
        # ensure Python version exists
        assert python_version is not None, "Failed to find python version"
        assert_function_in_collapsed(f"standard-library=={python_version}", process_collapsed)


@pytest.mark.parametrize(
    "runtime,profiler_type",
    RUNTIME_PROFILERS,
)
def test_from_container(
    docker_client: DockerClient,
    application_pid: int,
    runtime_specific_args: List[str],
    gprofiler_docker_image: Image,
    output_directory: Path,
    assert_collapsed: AssertInCollapsed,
    assert_application_name: Callable,
    profiler_flags: List[str],
) -> None:
    _ = application_pid  # Fixture only used for running the application.
    _ = assert_application_name  # Required for mypy unused argument warning
    collapsed_text = run_gprofiler_in_container_for_one_session(
        docker_client, gprofiler_docker_image, output_directory, runtime_specific_args, profiler_flags
    )
    collapsed = parse_one_collapsed(collapsed_text)
    assert_collapsed(collapsed)
