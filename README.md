
# Two-Qubit Tomography XPS Automation

Automated data collection, hardware control, and post-processing for two-qubit tomography experiments using Newport XPS controllers and the UQD Logic 16 Correlation Viewer software (V0.35 - 21.04.2021).

---

## 🚀 Overview

This repository provides:

- Automated four-stage motion control via the Newport XPS system (using the external `newportxps_control` library).
- Robust GUI automation (via PyAutoGUI) for UQD-driven data acquisition.
- Table-driven experiment sequencing using a simple `motion.txt` file, with support for custom file labels.
- Batch post-processing to extract averages from all generated CSV data files.
- After experiment completion, all stages return to their configured zero position as set in XPS config.

---

## 📁 Folder Structure

```
your_project/
│
├── newportxps_control/            # (NOT INCLUDED; must clone from its repo)
├── two_qubit_tomography_xps.py    # Main experiment automation
├── process_uqd_results.py         # Batch data analysis
├── run_experiment_and_process.py  # Main orchestrator
├── motion.txt                     # Your measurement table
├── saved_data/                    # Output data and averages
├── screenshots/                   # PNGs for GUI automation (see below)
└── README.md
```

---

## 🔗 Dependencies

- Python 3.7+
- [`newportxps_control`](https://github.com/ppalaciosa/newportxps_control) (clone into project root)
- [`newportxps`](https://pypi.org/project/newportxps/) Python package (**must be installed via pip**)
    ```sh
    pip install newportxps
    ```
- `pyautogui`, `pygetwindow`
- Standard scientific Python libraries (numpy, etc.)

---

## 🖼️ Required Screenshot Files

The following PNGs must be in your `screenshots/` folder for GUI automation. They are used to interact with UQD buttons and dialogs. All images should be tightly cropped screenshots from your UQD GUI.

| Filename                 | Purpose                                          |
|--------------------------|--------------------------------------------------|
| `csv_file_tag.png`       | Click "CSV" or "file save" button in UQD         |
| `save_file_dialog.png`   | Detect when Save As dialog appears               |
| `save2.png`              | (Optional) "Save" button in dialog (if used)     |
| `confirm_save_as.png`    | Confirm Save As dialog is focused/ready          |
| `start_data_collect.png` | Start data collection                            |
| `stop_data_collect.png`  | Stop data collection                             |
| `users.png`              | "CSV File" UQD's GUI tag    |

- If you get "template not found" errors, check for typos, cropping, or wrong folder.

> ⚠️ **Note:** The screenshot files in the `screenshots/` folder must be captured on the same computer and with the same screen resolution, scaling, and monitor arrangement as where you will run the UQD GUI. If any of these conditions change, the screenshot templates may no longer match!

---

## ⚙️ Setup

### 1. Clone this repository and the motion control library

```sh
git clone https://github.com/ppalaciosa/two_qubit_tomography.git
cd two_qubit_tomography
git clone https://github.com/ppalaciosa/newportxps_control.git
```

### 2. Install required Python dependencies

```sh
pip install newportxps pyautogui pygetwindow
```

### 3. Configure your XPS connection and hardware

- Follow the [newportxps_control](https://github.com/ppalaciosa/newportxps_control) setup for:
    - Creating `config/xps_connection_parameters.json`
    - Generating `config/xps_hardware.json`
    - Setting stage zero offsets if needed
- Place all required screenshots in the `screenshots/` folder.

### 4. Prepare your `motion.txt`

Example lines (4 positions, then optional label):
```
10.0, 0.0, 90.0, 5.0
20.0, 5.0, 45.0, 0.0, my_custom_label
```
The file `motion_tomography_kwiat.txt`  is included, containing a standard measurement sequence for two-qubit tomography as described by **James *et al.* (2001)** [[Phys. Rev. A 64, 052312](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.64.052312)].

---

## 🏃‍♂️ How To Run

### **Recommended: All-in-one Orchestrator**

```sh
python run_experiment_and_process.py --motion motion.txt --stages 1,2,3,4 -wait 10 --desc my_table_run --column "Pattern 01[counts]" --process
```

- Data files will be named `comboNNN.csv` or with your custom label.
- Averages for the specified column are written to `total_averages.csv` in the output folder.
- After all combos, **all stages are returned to their configured zero position** automatically.

### **Direct Use:**
- Run the experiment only: `python two_qubit_tomography_xps.py`
- Process data only: `python process_uqd_results.py saved_data/<folder> "Pattern 01[counts]"`

---

## 📄 motion.txt Format

- **4 comma-separated positions** (for each stage), then an **optional label**.
    ```
    45.0,0.0,45.0,0.0,HH
    0.0,0.0,45.0,0.0,VH
    ...
    ```
- Blank or `#`-commented lines are ignored.

---

## ⚠️ Troubleshooting & Tips

- **Move error or out-of-range:** Check motion.txt and your hardware limits in XPS config.
- **UQD window not found:** Ensure UQD is running, and the window title matches what the script expects.
- **Screenshot/template not found:** Check for cropping, file name, and display scaling.
- **All motion and zero-offset handling** is performed by `newportxps_control`—your combos are always relative to the logical zero.


---
## 📬 Author
Maintained by Pablo Palacios. Contributions welcome!
