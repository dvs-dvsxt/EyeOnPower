"""
EyeOnPower | 电量守望者
Windows 电池电量实时监测工具
功能：屏幕右下角置顶显示电量百分比、充电状态、剩余续航时间、当前时间日期
支持展开/折叠详细信息，支持切换置顶状态
"""

import sys
import time
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QProgressBar, QGroupBox, QGridLayout,
                             QScrollArea, QPushButton, QHBoxLayout, QFrame)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

# 忽略 PyQt5 的 DeprecationWarning
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 尝试导入 wmi
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# ============== WinAPI 结构体 ==============
AC_LINE_ONLINE = 1
BATTERY_LIFE_UNKNOWN = 0xFFFFFFFF

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', ctypes.c_byte),
        ('BatteryFlag', ctypes.c_byte),
        ('BatteryLifePercent', ctypes.c_byte),
        ('Reserved1', ctypes.c_byte),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]

def get_power_status():
    """调用 GetSystemPowerStatus API（最稳定）"""
    try:
        kernel32 = ctypes.windll.kernel32
        status = SYSTEM_POWER_STATUS()
        if kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return status
    except Exception as e:
        print(f"GetSystemPowerStatus 错误: {e}")
    return None

def safe_int(value, default=0):
    """安全地转换为整数"""
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            if value.strip().isdigit():
                return int(value)
            return default
        return default
    except:
        return default

def safe_str(value, default="未知"):
    """安全地转换为字符串"""
    try:
        if value is None:
            return default
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value:
            return str(value)
        return default
    except:
        return default

def format_remaining_time(seconds):
    """格式化剩余时间 - 过大则显示未知"""
    try:
        secs = safe_int(seconds, 0)
        if secs <= 0 or secs == BATTERY_LIFE_UNKNOWN or secs > 864000:
            return "未知"
        
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        if hours > 0:
            return f"{hours}小时 {minutes}分钟"
        else:
            return f"{minutes}分钟"
    except:
        return "未知"

def get_current_datetime():
    """获取当前日期时间字符串"""
    now = time.localtime()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d} {weekdays[now.tm_wday]} {now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}"

class EyeOnPower(QMainWindow):
    """电量守望者主窗口"""
    
    def __init__(self):
        super().__init__()
        self.battery_info = {}
        self.wmi_error = None
        self.detailed_visible = False  # 详细信息是否可见
        self.is_topmost = True  # 默认置顶状态
        
        # 获取 WMI 信息
        if WMI_AVAILABLE:
            try:
                wmi_conn = wmi.WMI()
                self.get_wmi_battery_info(wmi_conn)
            except Exception as e:
                self.wmi_error = f"WMI 初始化失败: {str(e)}"
                print(self.wmi_error)
        else:
            self.wmi_error = "wmi 模块未安装 (pip install wmi)"
        
        self.init_ui()
        
        # 设置定时器，每秒更新一次
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_battery_info)
        self.timer.start(1000)
        self.update_battery_info()
    
    def get_wmi_battery_info(self, wmi_conn):
        """通过 WMI 获取电池详细信息"""
        try:
            batteries = wmi_conn.Win32_Battery()
            for battery in batteries:
                # 电池状态
                self.battery_info['battery_status'] = safe_int(getattr(battery, 'BatteryStatus', None), 0)
                
                # 化学类型
                chem = getattr(battery, 'Chemistry', None)
                chem_int = safe_int(chem, 0)
                chemistry_map = {1: "其他", 2: "未知", 3: "铅酸", 4: "镍镉", 5: "镍氢", 
                                 6: "锂离子", 7: "锌空气", 8: "锂聚合物"}
                self.battery_info['chemistry'] = chemistry_map.get(chem_int, f"类型{chem_int}" if chem_int > 0 else "未知")
                
                # 容量信息
                self.battery_info['design_capacity'] = safe_int(getattr(battery, 'DesignCapacity', 0), 0)
                self.battery_info['full_capacity'] = safe_int(getattr(battery, 'FullChargeCapacity', 0), 0)
                self.battery_info['design_voltage'] = safe_int(getattr(battery, 'DesignVoltage', 0), 0)
                
                # 预估信息
                est_charge = getattr(battery, 'EstimatedChargeRemaining', None)
                self.battery_info['estimated_charge'] = safe_int(est_charge, None) if est_charge is not None else None
                
                est_time = getattr(battery, 'EstimatedRunTime', None)
                self.battery_info['estimated_run_time'] = safe_int(est_time, None) if est_time is not None else None
                
                time_to_full = getattr(battery, 'TimeToFullCharge', None)
                self.battery_info['time_to_full'] = safe_int(time_to_full, None) if time_to_full is not None else None
                
                # 基本信息
                self.battery_info['name'] = safe_str(getattr(battery, 'Name', None), "未知")
                self.battery_info['manufacturer'] = safe_str(getattr(battery, 'Manufacturer', None), "未知")
                self.battery_info['serial'] = safe_str(getattr(battery, 'SerialNumber', None), "未知")
                self.battery_info['device_id'] = safe_str(getattr(battery, 'DeviceID', None), "未知")
                self.battery_info['smart_version'] = safe_str(getattr(battery, 'SmartBatteryVersion', None), "未知")
                
                break
                
            if not self.battery_info:
                self.wmi_error = "未检测到电池"
                
        except Exception as e:
            self.wmi_error = f"WMI 获取失败: {str(e)}"
            print(self.wmi_error)
    
    def toggle_topmost(self):
        """切换窗口置顶状态"""
        if self.is_topmost:
            # 取消置顶：从窗口标志中移除置顶属性
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.topmost_btn.setText("📌 置顶 (关)")
            self.topmost_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 10px;
                    background-color: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            self.is_topmost = False
        else:
            # 设置置顶：添加置顶属性
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.topmost_btn.setText("📌 置顶 (开)")
            self.topmost_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 10px;
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)
            self.is_topmost = True
        
        # 关键：修改窗口标志后必须重新 show() 才会生效
        self.show()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("EyeOnPower - 电量守望者")
        
        # 初始小窗口大小
        self.setFixedSize(340, 270)
        
        # 默认设置窗口置顶标志
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # 获取屏幕尺寸，计算右下角位置
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20  # 距离右边20像素
        y = screen.height() - self.height() - 50  # 距离底部50像素（避开任务栏）
        self.move(x, y)
        
        # 创建中央窗口部件
        central = QWidget()
        central.setStyleSheet("background: #ecf0f1;")
        self.setCentralWidget(central)
        
        # 主布局
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ========== 标题栏（包含标题按钮和置顶按钮） ==========
        title_layout = QHBoxLayout()
        
        # 标题按钮（用于展开/折叠详细信息）
        self.title_button = QPushButton("👁️ 电量守望者  ▼")
        self.title_button.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.title_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self.title_button.clicked.connect(self.toggle_detailed_info)
        title_layout.addWidget(self.title_button)
        
        # 置顶切换按钮
        self.topmost_btn = QPushButton("📌 置顶 (开)")
        self.topmost_btn.setFont(QFont("Microsoft YaHei", 8))
        self.topmost_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 8px;
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.topmost_btn.clicked.connect(self.toggle_topmost)
        title_layout.addWidget(self.topmost_btn)
        
        self.main_layout.addLayout(title_layout)
        
        # ========== 日期时间区域 ==========
        datetime_frame = QFrame()
        datetime_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        datetime_layout = QHBoxLayout(datetime_frame)
        datetime_layout.setContentsMargins(8, 4, 8, 4)
        
        self.datetime_label = QLabel(get_current_datetime())
        self.datetime_label.setFont(QFont("Microsoft YaHei", 9))
        self.datetime_label.setStyleSheet("color: #ecf0f1;")
        self.datetime_label.setAlignment(Qt.AlignCenter)
        datetime_layout.addWidget(self.datetime_label)
        
        self.main_layout.addWidget(datetime_frame)
        
        # ========== 关键信息区域（始终显示） ==========
        key_group = QGroupBox("📊 电量实时监控")
        key_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 2px solid #3498db; 
                border-radius: 6px; 
                margin-top: 8px;
                font-size: 11px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
                color: #3498db;
            }
        """)
        key_layout = QGridLayout()
        key_layout.setSpacing(6)
        
        # 电量百分比（大字体）
        self.percent_label = QLabel("--%")
        self.percent_label.setFont(QFont("Arial", 32, QFont.Bold))
        self.percent_label.setStyleSheet("color: #2ecc71;")
        key_layout.addWidget(self.percent_label, 0, 0, 1, 2)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(18)
        key_layout.addWidget(self.progress, 1, 0, 1, 2)
        
        # 电源状态
        key_layout.addWidget(QLabel("电源状态:"), 2, 0)
        self.power_status = QLabel("--")
        self.power_status.setStyleSheet("color: #3498db; font-weight: bold;")
        key_layout.addWidget(self.power_status, 2, 1)
        
        # 剩余时间
        key_layout.addWidget(QLabel("剩余时间:"), 3, 0)
        self.remaining_time = QLabel("--")
        key_layout.addWidget(self.remaining_time, 3, 1)
        
        key_group.setLayout(key_layout)
        self.main_layout.addWidget(key_group)
        
        # ========== 详细信息区域（初始隐藏） ==========
        self.detailed_group = QGroupBox("🔧 电池详细信息")
        self.detailed_group.setVisible(False)
        self.detailed_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 2px solid #27ae60; 
                border-radius: 6px; 
                margin-top: 8px;
                background-color: #f8f9fa;
                font-size: 10px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
                color: #27ae60; 
            }
            QLabel { 
                padding: 2px;
                font-size: 10px;
            }
        """)
        
        # 使用 QScrollArea 使详细信息可滚动
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        detail_content = QWidget()
        detail_layout = QGridLayout(detail_content)
        detail_layout.setSpacing(4)
        detail_layout.setContentsMargins(6, 6, 6, 6)
        
        # 添加所有详细信息
        row = 0
        
        # 制造商
        detail_layout.addWidget(QLabel("制造商:"), row, 0)
        self.detail_manufacturer = QLabel("未知")
        detail_layout.addWidget(self.detail_manufacturer, row, 1)
        row += 1
        
        # 电池名称
        detail_layout.addWidget(QLabel("电池名称:"), row, 0)
        self.detail_name = QLabel("未知")
        detail_layout.addWidget(self.detail_name, row, 1)
        row += 1
        
        # 化学类型
        detail_layout.addWidget(QLabel("化学类型:"), row, 0)
        self.detail_chemistry = QLabel("未知")
        detail_layout.addWidget(self.detail_chemistry, row, 1)
        row += 1
        
        # 设计容量
        detail_layout.addWidget(QLabel("设计容量:"), row, 0)
        self.detail_design_cap = QLabel("未知")
        detail_layout.addWidget(self.detail_design_cap, row, 1)
        row += 1
        
        # 当前满充容量
        detail_layout.addWidget(QLabel("当前满充容量:"), row, 0)
        self.detail_full_cap = QLabel("未知")
        detail_layout.addWidget(self.detail_full_cap, row, 1)
        row += 1
        
        # 电池健康度
        detail_layout.addWidget(QLabel("电池健康度:"), row, 0)
        self.detail_health = QLabel("未知")
        self.detail_health.setStyleSheet("font-weight: bold;")
        detail_layout.addWidget(self.detail_health, row, 1)
        row += 1
        
        # 设计电压
        detail_layout.addWidget(QLabel("设计电压:"), row, 0)
        self.detail_voltage = QLabel("未知")
        detail_layout.addWidget(self.detail_voltage, row, 1)
        row += 1
        
        # 预估剩余电量
        detail_layout.addWidget(QLabel("预估剩余电量:"), row, 0)
        self.detail_estimated = QLabel("未知")
        detail_layout.addWidget(self.detail_estimated, row, 1)
        row += 1
        
        # 序列号
        detail_layout.addWidget(QLabel("序列号:"), row, 0)
        self.detail_serial = QLabel("未知")
        detail_layout.addWidget(self.detail_serial, row, 1)
        row += 1
        
        # 设备ID
        detail_layout.addWidget(QLabel("设备ID:"), row, 0)
        self.detail_device_id = QLabel("未知")
        detail_layout.addWidget(self.detail_device_id, row, 1)
        row += 1
        
        # 数据来源
        detail_layout.addWidget(QLabel("数据来源:"), row, 0)
        self.detail_source = QLabel("Win32 API + WMI")
        self.detail_source.setStyleSheet("color: #2ecc71; font-weight: bold;")
        detail_layout.addWidget(self.detail_source, row, 1)
        row += 1
        
        # WMI 错误提示
        if self.wmi_error:
            error_label = QLabel(f"⚠️ {self.wmi_error}")
            error_label.setStyleSheet("color: #e74c3c; font-size: 9px;")
            detail_layout.addWidget(error_label, row, 0, 1, 2)
        
        detail_content.setLayout(detail_layout)
        detail_scroll.setWidget(detail_content)
        
        detail_group_layout = QVBoxLayout()
        detail_group_layout.addWidget(detail_scroll)
        self.detailed_group.setLayout(detail_group_layout)
        
        self.main_layout.addWidget(self.detailed_group)
        
        # 添加弹性空间
        self.main_layout.addStretch()
    
    def toggle_detailed_info(self):
        """切换详细信息显示"""
        self.detailed_visible = not self.detailed_visible
        self.detailed_group.setVisible(self.detailed_visible)
        
        # 获取当前屏幕尺寸
        screen = QApplication.primaryScreen().geometry()
        
        # 更新按钮文字和窗口大小
        if self.detailed_visible:
            self.title_button.setText("👁️ 电量守望者  ▲")
            self.setFixedSize(380, 550)
        else:
            self.title_button.setText("👁️ 电量守望者  ▼")
            self.setFixedSize(340, 270)
        
        # 重新计算右下角位置
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 50
        self.move(x, y)
    
    def update_battery_info(self):
        """更新所有电池信息"""
        try:
            # 更新时间日期
            self.datetime_label.setText(get_current_datetime())
            
            # ===== Win32 API（关键信息） =====
            status = get_power_status()
            if status:
                percent = status.BatteryLifePercent
                if percent != 255:
                    self.percent_label.setText(f"{percent}%")
                    self.progress.setValue(percent)
                    if percent <= 20:
                        self.progress.setStyleSheet("QProgressBar::chunk { background: #e74c3c; border-radius: 4px; }")
                    elif percent <= 50:
                        self.progress.setStyleSheet("QProgressBar::chunk { background: #f39c12; border-radius: 4px; }")
                    else:
                        self.progress.setStyleSheet("QProgressBar::chunk { background: #2ecc71; border-radius: 4px; }")
                else:
                    self.percent_label.setText("未知")
                
                acline = status.ACLineStatus
                battery_flag = status.BatteryFlag
                
                if acline == 1:
                    self.power_status.setText("🔌 交流电供电")
                    self.remaining_time.setText("正在充电")
                else:
                    if battery_flag & 2:
                        self.power_status.setText("⚡ 正在充电")
                    elif battery_flag & 4:
                        self.power_status.setText("✅ 完全充满")
                    elif battery_flag & 8:
                        self.power_status.setText("⚠️ 电量低")
                    else:
                        self.power_status.setText("🔋 使用电池")
                    time_text = format_remaining_time(status.BatteryLifeTime)
                    self.remaining_time.setText(time_text)
            
            # ===== 更新详细信息（如果可见） =====
            if self.detailed_visible and self.battery_info and not self.wmi_error:
                self.detail_manufacturer.setText(self.battery_info.get('manufacturer', '未知'))
                self.detail_name.setText(self.battery_info.get('name', '未知'))
                self.detail_chemistry.setText(self.battery_info.get('chemistry', '未知'))
                
                # 设计容量
                design = self.battery_info.get('design_capacity', 0)
                if design and design > 0:
                    self.detail_design_cap.setText(f"{design} mWh ({design/1000:.1f} Wh)")
                else:
                    self.detail_design_cap.setText("未知")
                
                # 满充容量
                full = self.battery_info.get('full_capacity', 0)
                if full and full > 0:
                    self.detail_full_cap.setText(f"{full} mWh ({full/1000:.1f} Wh)")
                else:
                    self.detail_full_cap.setText("未知")
                
                # 电池健康度
                design_val = self.battery_info.get('design_capacity', 0)
                full_val = self.battery_info.get('full_capacity', 0)
                if design_val and design_val > 0 and full_val and full_val > 0:
                    health = (full_val / design_val) * 100
                    if health > 100:
                        health = 100
                    self.detail_health.setText(f"{health:.1f}%")
                    if health >= 80:
                        self.detail_health.setStyleSheet("color: #2ecc71; font-weight: bold;")
                    elif health >= 60:
                        self.detail_health.setStyleSheet("color: #f39c12; font-weight: bold;")
                    else:
                        self.detail_health.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.detail_health.setText("未知")
                
                # 设计电压
                voltage = self.battery_info.get('design_voltage', 0)
                if voltage and voltage > 0:
                    self.detail_voltage.setText(f"{voltage} mV ({voltage/1000:.2f} V)")
                else:
                    self.detail_voltage.setText("未知")
                
                # 预估剩余电量
                est_charge = self.battery_info.get('estimated_charge')
                if est_charge is not None and est_charge > 0:
                    self.detail_estimated.setText(f"{est_charge}%")
                else:
                    self.detail_estimated.setText("未知")
                
                self.detail_serial.setText(self.battery_info.get('serial', '未知'))
                self.detail_device_id.setText(self.battery_info.get('device_id', '未知'))
            
        except Exception as e:
            print(f"更新出错: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        event.accept()


def main():
    """程序入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont("Microsoft YaHei", 9))
    
    window = EyeOnPower()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()