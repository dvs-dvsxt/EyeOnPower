# 🪫 EyeOnPower — Battery Monitor

> A real-time **Windows battery level monitor** that displays battery percentage, charging status, remaining time, and current date/time in a always-on-top corner widget.

**EyeOnPower** is a lightweight desktop widget that sits in the bottom-right corner of your screen, showing your battery level at a glance. It supports expanding/collapsing detailed battery info, and toggling window always-on-top.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔋 **Real-time Battery %** | Live battery percentage display with large font & progress bar |
| 🔌 **Charging Status** | AC power / charging / fully charged / low battery indicators |
| ⏱️ **Remaining Time** | Estimated remaining battery life (hours & minutes) |
| 📅 **Date & Time** | Current date, weekday, and time always visible |
| 🔍 **Detailed Info** | Expandable battery details (manufacturer, capacity, health, voltage, serial...) |
| 📌 **Always-on-Top** | Toggleable window pinning |
| 🔗 **Dual Data Source** | Win32 API (`GetSystemPowerStatus`) + WMI (`Win32_Battery`) |

### Detailed Battery Info (expandable)
- Manufacturer / Battery name
- Chemistry type (Li-ion, Li-polymer, etc.)
- Design capacity & full charge capacity (mWh / Wh)
- **Battery health %** (full/design capacity ratio, color-coded)
- Design voltage (mV / V)
- Estimated charge remaining
- Serial & Device ID

---

## 🚀 Quick Start

### Prerequisites
- Windows (laptop / notebook with battery)
- Python 3.7+

### Install & Run from Source

```bash
# Install dependencies
pip install PyQt5 wmi

# Run
python EyeOnPower.py
```

### Run the Compiled EXE
Just double-click `EyeOnPower.exe` — no Python required.

---

## 🎮 Usage

- **Title bar button** (`👁️ 电量守望者`): expand / collapse detailed battery info
- **Pin button** (`📌 置顶`): toggle always-on-top
- Widget automatically stays in the bottom-right corner

---

## 📦 Project Structure

```
EyeOnPower/
├── EyeOnPower.py    # Main program (PyQt5 battery monitor)
├── EyeOnPower.exe   # Compiled executable (no Python needed)
└── README.md        # This document
```

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 🙏 Note

> ✓ The widget is **always-on-top** by default, so it stays visible above other windows.
> ✓ Low battery warning: progress bar turns **red** at ≤20%, **orange** at ≤50%, green otherwise.
> ✓ Battery health is color-coded: **green** ≥80%, **orange** ≥60%, **red** below.
