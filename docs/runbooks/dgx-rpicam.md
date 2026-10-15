# Runbook: DGX Spark → RPi5 USB Camera (seam, sensing)

This runbook validates communication between a **DGX Spark brain** and a **Raspberry Pi 5 with a USB camera** using the OpenPAVE seam plugin.

The `get_image` capability requests a fresh camera frame from the RPi5.

> **Important:** `get_image` through `seam_run.sh` returns control-plane metadata only. The JPEG image bytes use a separate data plane and are not displayed or transferred by this test.

## Setup

| Dimension | Value |
|---|---|
| Brain | DGX Spark |
| Body | Raspberry Pi 5 + USB camera |
| Camera adapter | `camera_usb` |
| Camera device | `/dev/video0` |
| Transport | `raw_zenoh` / `device_connect` |
| Capability | `get_image` |

Three machines are used during setup:

- **Local machine** – used to clone OpenPAVE and deploy the seam bundle (Mac in this example)
- **DGX Spark** – runs the seam brain
- **RPi5** – runs the camera body

---

# 1. Prepare OpenPAVE on the local machine

**Run on: Local machine**

Clone OpenPAVE:

```bash
git clone https://github.com/odincodeshen/OpenPAVE.git
cd OpenPAVE
```

Fetch the available tags and checkout the seam release:

```bash
git fetch --tags
git checkout v1.5.0-seam
```

Verify the required files exist:

```bash
ls requirements-seam.txt
ls scripts/deploy_seam.sh
```

> In `v1.5.0-seam`, the camera configuration is named:
>
> `configs/dgx-camera.env`
>
> Later versions of the repository rename this to `configs/dgx-rpicam.env`.

---

# 2. Prepare the DGX Python environment

**Run on: DGX Spark**

Check Python:

```bash
python3 --version
```

Create the virtual environment expected by the seam scripts:

```bash
python3 -m venv ~/.venv-zenoh
```

Verify:

```bash
~/.venv-zenoh/bin/python --version
```

---

# 3. Deploy the seam bundle to the DGX

First determine the DGX IP address.

**Run on: DGX Spark**

```bash
hostname -I
```

For example:

```text
10.1.52.72
```

Return to the OpenPAVE checkout on the local machine.

**Run on: Local machine**

```bash
cd OpenPAVE
```

Deploy the seam bundle:

```bash
scripts/deploy_seam.sh <DGX_USER>@<DGX_IP> '$HOME/openpave-seam' '$HOME/.venv-zenoh/bin/python'
```

Example:

```bash
scripts/deploy_seam.sh dgx@10.1.52.72 '$HOME/openpave-seam' '$HOME/.venv-zenoh/bin/python'
```

Enter the SSH password if prompted and allow the deployment to complete.

Verify the deployment.

**Run on: DGX Spark**

```bash
cd ~/openpave-seam
ls requirements-seam.txt
```

Install the DGX seam dependencies:

```bash
~/.venv-zenoh/bin/pip install -r requirements-seam.txt
```

---

# 4. Prepare the RPi5

The RPi5 requires a clean OpenPAVE checkout.

**Run on: RPi5**

```bash
git clone https://github.com/odincodeshen/OpenPAVE.git ~/OpenPAVE
cd ~/OpenPAVE
```

If the repository already exists:

```bash
cd ~/OpenPAVE
git fetch --tags
```

Checkout the seam release:

```bash
git checkout v1.5.0-seam
```

Verify:

```bash
git describe --tags --always
```

Expected:

```text
v1.5.0-seam
```

Create the Python environment:

```bash
python3 -m venv ~/.venv-zenoh
```

Verify:

```bash
~/.venv-zenoh/bin/python --version
```

Install the seam and camera dependencies:

```bash
~/.venv-zenoh/bin/pip install \
  -r requirements-seam.txt \
  -r requirements-seam-camera.txt
```

---

# 5. Determine the DGX and RPi5 IP addresses

The supplied configuration contains example LAN addresses. These **must be replaced with the addresses of the machines being used**.

### DGX Spark

**Run on: DGX Spark**

```bash
hostname -I
```

Example:

```text
10.1.16.84
```

### RPi5

**Run on: RPi5**

```bash
hostname -I
```

Example:

```text
10.1.16.50
```

Record both addresses:

```text
DGX IP:  <DGX_IP>
RPi IP:  <RPI_IP>
```

---

# 6. Update the camera configuration

Both machines must use the correct addresses.

For `v1.5.0-seam`, edit:

```text
configs/dgx-camera.env
```

## RPi5

**Run on: RPi5**

```bash
cd ~/OpenPAVE
nano configs/dgx-camera.env
```

Update:

```text
BRAIN_HOST=<DGX_IP>
BODY_HOST=<RPI_IP>
```

For example:

```text
BRAIN_HOST=10.1.16.84
BODY_HOST=10.1.16.50
```

Save and exit.

## DGX Spark

**Run on: DGX Spark**

```bash
nano ~/openpave-seam/configs/dgx-camera.env
```

Make the same changes:

```text
BRAIN_HOST=<DGX_IP>
BODY_HOST=<RPI_IP>
```

The `BRAIN_HOST` and `BODY_HOST` values must match on both machines.

---

# 7. Start the RPi5 camera body

**Run on: RPi5**

```bash
cd ~/OpenPAVE
./scripts/seam_run.sh configs/dgx-camera.env body
```

A successful startup should include output similar to:

```text
[seam_run] recipe=dgx-camera.env role=body transport=raw_zenoh
[seam:raw_zenoh] body up · adapter=camera_usb · caps=['get_image']
```

**Leave this terminal running.**

The RPi5 is now waiting for requests from the DGX.

---

# 8. Request an image from the DGX

Open/use another terminal connected to the DGX.

**Run on: DGX Spark**

```bash
cd ~/openpave-seam
./scripts/seam_run.sh configs/dgx-camera.env brain send get_image
```

A successful request should return a result similar to:

```text
{
  "status": "success",
  "action": "get_image",
  "updated": {
    "encoding": "jpeg",
    "bytes": 6878,
    "width": 640,
    "height": 480,
    "source": "/dev/video0",
    "seq": 1
  },
  "error": null
}
```

The exact byte count and sequence number may differ.

The important fields are:

```text
"status": "success"
"action": "get_image"
"source": "/dev/video0"
"error": null
```

This confirms that:

1. The DGX can communicate with the RPi5.
2. The RPi5 camera body received the request.
3. The USB camera was accessed through `/dev/video0`.
4. A frame was captured successfully.
5. Camera metadata was returned to the DGX.

---

# 9. Control plane vs data plane

A successful `get_image` request does **not** display the captured image.

The seam request returns metadata such as:

```text
encoding
bytes
width
height
source
seq
```

The JPEG itself travels over a separate data plane.

---


# Troubleshooting

## `~/.venv-zenoh/bin/python: No such file or directory`

The required virtual environment does not exist.

Create it:

```bash
python3 -m venv ~/.venv-zenoh
```

Then install the appropriate dependencies.

---

## `Could not open requirements file: requirements-seam.txt`

The command is being run from a directory that does not contain the requirements file.

On the DGX:

```bash
cd ~/openpave-seam
```

On the RPi5:

```bash
cd ~/OpenPAVE
```

Then retry the installation.

---

## `recipe not found: configs/dgx-rpicam.env`

When using `v1.5.0-seam`, the configuration is called:

```text
configs/dgx-camera.env
```

Use:

```bash
./scripts/seam_run.sh configs/dgx-camera.env ...
```

The `dgx-rpicam.env` name belongs to a later repository revision.

---

## `status: no_reply` / `error: timeout`

First verify that the RPi5 body is still running.

If it is, check the IP addresses in the configuration.

Both machines should have:

```text
BRAIN_HOST=<actual DGX IP>
BODY_HOST=<actual RPi5 IP>
```

Do not leave the example `192.168.x.x` addresses in the configuration unless they are actually correct for your network.

After changing the configuration, restart the RPi5 body before retrying the DGX request.

---

# Validation

The `raw_zenoh` path is successfully validated when the RPi5 reports:

```text
body up · adapter=camera_usb · caps=['get_image']
```

and the DGX `get_image` request returns:

```text
"status": "success"
```

with valid JPEG metadata and:

```text
"error": null
```