""" CLI wrapper for Apple Container service. """
__author__ = "Wolf Paulus"
__copyright__ = "Copyright 2026, wolfpaulus.com"
__license__ = "MIT License"
__version__ = "1.0"
__email__ = "wolf@paulus.com"

import os
import json
from pathlib import Path
import subprocess
from typing import Any
from logging_config import logger

LABEL = "spyglass"
RMI_LABEL = "spyglass_rmi"


def container_command(*args: str) -> str | None:
    """ Call the container command with the given arguments and return the output. """
    logger.debug(f"Running container command: {' '.join(args)}")
    try:
        result = subprocess.run(
            ["container", *args],
            capture_output=True,
            text=True,
            check=True
        )
        logger.debug(f"Command output: {result.stdout}")

        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing container command: {e}")
        print(e)
        return None


def cmd_container_list() -> list[dict[Any, Any]]:
    """ Returns a List of images """
    logger.info("Listing all containers with label 'spyglass'")
    if s := container_command("list", "--all", "--format", "json"):
        # labels field is a dictionry, we are looking for a "spyglass" key.
        return [c for c in json.loads(s) if c["configuration"]["labels"].get(LABEL, False) == "true"]
    return []


def cmd_img_list() -> list[dict[Any, Any]]:
    """ Returns a List of all labeled containers"""
    logger.info("Listing all images")
    if s := container_command("image", "list", "--format", "json"):
        return json.loads(s)
    logger.error("Failed to list images or returned no data.")
    return []


def cmd_inspect(container_id: str) -> dict[Any, Any]:
    """ Returns detailed container info for a given container ID """
    logger.info(f"Inspecting container: {container_id}")
    result = container_command("inspect", container_id)
    if result and len(result) > 0:
        return json.loads(result)[0]
    logger.error(f"Inspecting container: {container_id} failed or returned no data.")
    return {}


def cmd_start(container_id: str) -> None:
    """ Start a container by its ID """
    result = container_command("start", container_id)
    logger.info(f"Starting container {container_id}: {result}")


def cmd_img_digest(image: str) -> str | None:
    """ Get the digest of a given image reference """
    logger.info(f"Getting image digest for: {image}")
    if s := container_command("image", "inspect", image):
        images = json.loads(s)
        return images[0]["configuration"]["descriptor"]["digest"]
    logger.error(f"Getting image digest for {image} failed or returned no data.")
    return None


def cmd_pull(image: str) -> bool:
    """ Pull the latest image for a given image reference """
    result = container_command("image", "pull", image)
    if result is not None:
        logger.info(f"Successfully pulled image {image}. {result}")
    else:
        logger.error(f"Failed to pull image {image}.")
    return result is not None


def get_user_spec(user: dict[Any, Any]) -> str | None:
    """Normalize Apple Container user representations."""
    # Tahoe
    if "raw" in user:
        return user["raw"].get("userString")

    # Golden Gate
    if "id" in user:
        uid = user["id"].get("uid")
        gid = user["id"].get("gid")

        if uid is not None and gid is not None:
            return f"{uid}:{gid}"

    return None


def image_reference_with_digest(reference: str, digest: str) -> str:
    """Return an image reference pinned to a digest, removing any tag."""
    reference = reference.split("@", 1)[0]
    last_component = reference.rsplit("/", 1)[-1]
    if ":" in last_component:
        reference = reference.rsplit(":", 1)[0]
    return f"{reference}@{digest}"


def merge(env: list[str], ef: str) -> list[str]:
    """ merge explicitly maintained environment variables """
    d: dict[str, str] = {}
    for elem in env:  # env found in running container
        l = elem.strip().split("=", 1)
        if len(l) == 2:
            d[l[0]] = l[1]

    with open(ef, encoding="utf-8") as f:
        for line in f.readlines():  # env found in file
            l = line.strip().split("=", 1)
            if len(l) == 2:
                d[l[0]] = l[1]
    return [f"{k}={v}" for k, v in d.items()]


def recreate(c: dict[Any, Any], image_reference: str | None = None) -> list[str]:
    """
    Build the container run command from container inspect JSON.
    c:         One container object from container inspect.
    Returns the command as a list suitable for subprocess.run().
    """
    name = c["configuration"]["id"]
    cmd: list[str] = ["run", "--detach", "--name", name]

    # Put the environment variables inherited and owned into an env file
    env_dir = Path.home() / "Library" / "Application Support" / "Spyglass" / "env"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_file = env_dir / f"{name}.env"

    env: list[str] = c["configuration"]["initProcess"]["environment"]
    if ef := c["configuration"]["labels"].get("spyglass_env_file"):
        env = merge(env, ef)
    if any("\n" in item or "\r" in item for item in env):
        raise ValueError("Multiline environment variables need special handling")
    env_file.write_text("\n".join(env) + "\n")
    os.chmod(env_file, 0o600)
    cmd += ["--env-file", str(env_file)]

    # Process configuration
    cmd += ["--entrypoint", c["configuration"]["initProcess"]["executable"]]

    if "workingDirectory" in c["configuration"]["initProcess"]:
        cmd += ["--workdir",  c["configuration"]["initProcess"]["workingDirectory"]]

    if user_spec := get_user_spec(c["configuration"]["initProcess"]["user"]):
        cmd += ["--user", user_spec]

    if c["configuration"]["initProcess"]["terminal"]:
        cmd.append("--tty")

    # Resource limits
    if "cpus" in c["configuration"]["resources"]:
        cmd += ["--cpus", str(c["configuration"]["resources"]["cpus"])]

    if "memoryInBytes" in c["configuration"]["resources"]:
        cmd += ["--memory", f"{c["configuration"]["resources"]["memoryInBytes"] / (1024 ** 3):g}G"]

    # Labels
    for key, value in c["configuration"]["labels"].items():
        cmd += ["--label", f"{key}={value}"]

    # Published ports
    for port in c["configuration"]["publishedPorts"]:
        host = port.get("hostAddress", "")
        spec = (
            f'{host + ":" if host else ""}'
            f'{port["hostPort"]}:{port["containerPort"]}'
            f'/{port.get("proto", "tcp")}'
        )
        cmd += ["--publish", spec]

    # Persistent mounts
    for mount in c["configuration"]["mounts"]:
        destination = mount["destination"]
        mount_type = mount.get("type", {})

        if "volume" in mount_type:
            source = mount_type["volume"]["name"]
        else:
            source = mount["source"]

        options = mount.get("options", [])
        suffix = ":ro" if "ro" in options or "readonly" in options else ""

        cmd += ["--volume", f"{source}:{destination}{suffix}"]

    # Networks
    for network in c["configuration"]["networks"]:
        options = network.get("options", {})
        spec = network["network"]

        if options.get("mtu"):
            spec += f',mtu={options["mtu"]}'

        if options.get("macAddress"):
            spec += f',mac={options["macAddress"]}'

        cmd += ["--network", spec]

    # DNS
    for value in c["configuration"]["dns"]["nameservers"]:
        cmd += ["--dns", value]

    for value in c["configuration"]["dns"]["options"]:
        cmd += ["--dns-option", value]

    for value in c["configuration"]["dns"]["searchDomains"]:
        cmd += ["--dns-search", value]

    # Other runtime settings
    for value in c["configuration"]["capAdd"]:
        cmd += ["--cap-add", value]

    for value in c["configuration"]["capDrop"]:
        cmd += ["--cap-drop", value]

    for key, value in c["configuration"]["sysctls"].items():
        cmd += ["--sysctl", f"{key}={value}"]

    if c["configuration"]["readOnly"]:
        cmd.append("--read-only")

    if c["configuration"]["useInit"]:
        cmd.append("--init")

    if c["configuration"]["rosetta"]:
        cmd.append("--rosetta")

    if c["configuration"]["ssh"]:
        cmd.append("--ssh")

    if c["configuration"]["virtualization"]:
        cmd.append("--virtualization")

    if (
        c["configuration"]["platform"].get("os")
        and c["configuration"]["platform"].get("architecture")
    ):
        p = c["configuration"]["platform"]
        cmd += [
            "--platform",
            f'{p["os"]}/{p["architecture"]}'
        ]

    # Image and original process arguments
    cmd.append(image_reference or c["configuration"]["image"]["reference"])
    cmd.extend(c["configuration"]["initProcess"]["arguments"])
    logger.info(f"Recreating command for container {name}: {' '.join(cmd)}")
    return cmd


def cmd_delete_image(name: str, digest: str) -> None:
    """ Delete an outdated image, if it exists """
    for image in cmd_img_list():
        image_config = image["configuration"]
        if (
            image_config["name"] == name
            and image_config["descriptor"]["digest"] == digest
        ):
            logger.info(f"Deleting outdated image {name} with digest {digest}")
            container_command("image", "delete", image["id"])
            return
    logger.warning(f"No outdated image found for {name} with digest {digest}, skipping deletion.")


def stop_rm(container: dict[Any, Any]) -> bool:
    """ Stop and delete container """
    if container["status"]["state"] == "running":
        logger.info(f"Stopping container {container["id"]}")
        container_command("stop", container["id"])
    logger.info(f"Deleting container {container["id"]}")
    container_command("delete", container["id"])
    if any(c["id"] == container["id"] for c in cmd_container_list()):
        logger.error(f"Container {container['id']} still exists after deletion.")
        return False
    return True


def post_launch(old_c: dict[Any, Any], new_digest: str) -> None:
    """ Check if the container is running """
    c = cmd_inspect(old_c["id"])
    if c and c["status"]["state"] == "running" and \
            c["configuration"]["image"]["descriptor"]["digest"] == new_digest:
        if not old_c["configuration"]["labels"].get(RMI_LABEL, True) == "false":
            logger.info(f"Removing image {old_c["configuration"]["image"]["descriptor"]["digest"]}")
            cmd_delete_image(old_c["configuration"]["image"]["reference"],
                             old_c["configuration"]["image"]["descriptor"]["digest"])
    else:  # Try to recover
        logger.error("Launch after recreate failed. Now trying to recreate the old container")
        if c:
            if not stop_rm(c):
                logger.error("Recovery failed!")
                return
        cmd_delete_image(old_c["configuration"]["image"]["reference"], new_digest)
        image = old_c["configuration"]["image"]
        rollback_reference = image_reference_with_digest(
            image["reference"],
            image["descriptor"]["digest"],
        )
        if launch_cmd := recreate(old_c, rollback_reference):
            container_command(*launch_cmd)
            c = cmd_inspect(old_c["id"])
            if c and c["status"]["state"] == "running" and \
                    c["configuration"]["image"]["descriptor"]["digest"] == image["descriptor"]["digest"]:
                logger.info("Recovery succeeded")
            else:
                img = json.dumps(c["configuration"]["image"]) if c else ""
                status = json.dumps(c["status"]) if c else ""
                logger.error(f"Recovery failed\n{img}\n{status}\n")


def check(cl: list[dict[Any, Any]] | None = None) -> None:
    """
    Start all stopped containers with the spyglass label
    Pull the latest image for all containers with the spyglass label
    Accept a pre-fetched container list to avoid repeated queries and support testing.
    """
    if cl is None:
        cl = cmd_container_list()
    for c in cl:
        logger.info(f"\n Checking container: {c["id"]}")
        # Pull the latest image from Registry
        if cmd_pull(c["configuration"]["image"]["reference"]):
            # Compare pull image's digest with container's image digest
            digest = cmd_img_digest(c["configuration"]["image"]["reference"])
            if digest == c["configuration"]["image"]["descriptor"]["digest"]:
                logger.info("Up to date")
            elif digest is not None:
                logger.info("Update available")
                if launch_cmd := recreate(c):
                    if stop_rm(c):
                        container_command(*launch_cmd)
                        post_launch(c, digest)
                continue
        if c["status"]["state"] == "stopped":
            cmd_start(c["id"])
