""" Test that stopped labeled containers get started.  """
__author__ = "Wolf Paulus"
__copyright__ = "Copyright 2026, wolfpaulus.com"
__license__ = "MIT License"
__version__ = "1.0"
__email__ = "wolf@paulus.com"

from pathlib import Path
from typing import Any
from container_manager import (
    container_command,
    check,
    cmd_inspect,
    cmd_container_list,
    recreate,
    post_launch,
    stop_rm,
)


C1 = "run \
--name c1 \
--detach \
--cpus 1 \
--memory 1G \
--publish 8003:8000 \
--volume c1_logs:/var/log \
--env-file /Users/wolf/VSC/spyglass/tests/c1_env_file \
docker.io/python:alpine"

C2 = "run \
--name c2 \
--detach \
--cpus 1 \
--memory 1G \
--label spyglass=true \
--label spyglass_env_file=/Users/wolf/VSC/spyglass/tests/c2_env_file \
--publish 8004:8000 \
--volume c2_logs:/var/log \
--env-file /Users/wolf/VSC/spyglass/tests/c2_env_file \
docker.io/library/python:3.15-slim-trixie \
python3.15 \
-m http.server \
8000 \
--bind 0.0.0.0"


def setup():
    """ Create two test containers, one labeled and one not labeled. """
    container_command(*C1.split())
    container_command(*C2.split())


def teardown():
    """ Stop and remove the test containers """
    for container_name in ["c1", "c2"]:
        try:
            container_command("stop", container_name)
            container_command("delete", container_name)
        except Exception as e:
            print(f"Error stopping/removing container {container_name}: {e}")


def container_restart():
    """ Test that stopped labeled containers get started.  """
    container_command("stop", "c1")
    container_command("stop", "c2")
    print("==========", cmd_inspect("c1"))
    assert cmd_inspect("c1")["status"]["state"] == "stopped"
    assert cmd_inspect("c2")["status"]["state"] == "stopped"
    # Run the check function to start stopped labeled containers
    check()
    # Verify that c2 is now running
    assert cmd_inspect("c1")["status"]["state"] == "stopped"
    assert cmd_inspect("c2")["status"]["state"] == "running"


def container_image_update():
    """ Test that outdated images are updated and containers are recreated. """
    container_command("start", "c2")
    # manipulate the container to simulate an outdated image
    digest = cmd_inspect("c2")["configuration"]["image"]["descriptor"]["digest"]
    created = cmd_inspect("c2")["configuration"]["creationDate"]
    for c in (cl := cmd_container_list()):
        if c["id"] == "c2":
            c["configuration"]["image"]["descriptor"]["digest"] = "outdated_digest"
    check(cl)
    # Verify that c2 has been recreated with the latest image
    d = cmd_inspect("c2")
    assert d["status"]["state"] == "running"
    assert d["configuration"]["image"]["descriptor"]["digest"] == digest
    assert d["configuration"]["creationDate"] != created, "Container c2 was not recreated"


def environment_merge():
    """ Test merging a given environment file """
    c: dict[Any, Any] = cmd_inspect("c2")
    ef: str = c["configuration"]["labels"]["spyglass_env_file"]
    d: dict[str, str] = {}

    # update a variable in the env-file:
    with open(ef, encoding="utf-8") as f:
        for line in f.readlines():
            l = line.strip().split("=", 1)
            if len(l) == 2:
                d[l[0]] = l[1]
    # current value is in the environment
    assert f"v1={d['v1']}" in c["configuration"]["initProcess"]["environment"]
    # increment by one
    d["v1"] = str(int(d["v1"]) + 1)
    with open(ef, "w", encoding="utf-8") as f:
        for k, v in d.items():
            f.write(f"{k}={v}\n")

    # build recreate command:
    _ = recreate(c)
    # inspect the temp file created for the env-file
    q: dict[str, str] = {}
    env_dir = Path.home() / "Library" / "Application Support" / "Spyglass" / "env"
    env_file = env_dir / f"{c['id']}.env"

    with open(env_file, encoding="utf-8") as f:
        for line in f.readlines():
            l = line.strip().split("=", 1)
            if len(l) == 2:
                q[l[0]] = l[1]
    assert q["v1"] == d["v1"]


def stopping_removing():
    """Remove a real running container and verify it is gone."""
    c = cmd_inspect("c2")
    assert c["status"]["state"] == "running"
    assert stop_rm(c)
    assert all(c["id"] != "c2" for c in cmd_container_list())
    container_command(*C2.split())


def recover():
    c = cmd_inspect("c2")
    assert c["status"]["state"] == "running"
    # trigger stop and relauch of c2
    post_launch(c, "not_a_real_digest")
    d = cmd_inspect("c2")
    assert d["status"]["state"] == "running"
    assert d["status"]["startedDate"] != c["status"]["startedDate"]


def test_all():
    """ Test that stopped labeled containers get started.  """
    try:
        setup()
        container_restart()
        container_image_update()
        environment_merge()
        stopping_removing()
        recover()
    finally:
        teardown()
