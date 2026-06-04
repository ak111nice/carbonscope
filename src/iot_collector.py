"""
IoT 数据采集接口 — MODBUS 模拟器 + 自动采集定时器
====================================================
用途：
  模拟工厂 IoT 网关，提供三层能力：
  1. ModbusSimulator — MODBUS RTU/TCP 寄存器模拟，8 块仪表
  2. AutoCollector  — 后台定时采集 + 自动保存 CSV
  3. 命令行自测    — python iot_collector.py 直接运行

工业协议依赖：
  - MODBUS RTU (RS-485 串行总线)：工厂最常见的仪表通信协议
  - 真实对接只需将 ModbusSimulator 替换为 pymodbus 的 ModbusTcpClient

仪表清单（8 路）：
  0x0100 主变电表_总用电量      (0-65535 MWh)
  0x0101 主变电表_当前功率      (0-5000 kW)
  0x0102 车间1_电表            (0-65535 MWh)
  0x0103 车间2_电表            (0-65535 MWh)
  0x0200 天然气总流量计         (0-100 万m³)
  0x0201 天然气_锅炉房         (0-50 万m³)
  0x0300 煤仓_皮带秤           (0-2000 吨)
  0x0301 柴油_地磅             (0-200 吨)

使用示例：
  >>> simulator = ModbusSimulator()
  >>> readings = simulator.read_all()
  >>> energy = simulator.map_to_energy(readings)
  >>> print(energy)  # {'电网电力': 12345.67, '天然气': 8.92, ...}

  >>> collector = AutoCollector(interval_seconds=60)
  >>> collector.start()   # 后台启动，每 60 秒采集一次
  >>> collector.get_latest()  # 获取最近一次能耗数据
  >>> collector.stop()
"""

import json
import time
import random
import os
from datetime import datetime, timedelta
from threading import Thread


# ============================================
# MODBUS 寄存器模拟器（演示用）
# ============================================
class ModbusSimulator:
    """模拟工厂能源数据采集系统（MODBUS RTU/TCP）"""

    registers = {
        # 地址: (名称, 最小值, 最大值, 单位)
        0x0100: ("主变电表_总用电量", 0, 65535, "MWh"),
        0x0101: ("主变电表_当前功率", 0, 5000, "kW"),
        0x0102: ("车间1_电表", 0, 65535, "MWh"),
        0x0103: ("车间2_电表", 0, 65535, "MWh"),
        0x0200: ("天然气总流量计", 0, 100, "万m³"),
        0x0201: ("天然气_锅炉房", 0, 50, "万m³"),
        0x0300: ("煤仓_皮带秤", 0, 2000, "吨"),
        0x0301: ("柴油_地磅", 0, 200, "吨"),
    }

    def __init__(self):
        self.current_values = {}
        for addr, (name, min_v, max_v, unit) in self.registers.items():
            self.current_values[addr] = random.uniform(min_v * 0.1, max_v * 0.3)

    def read_register(self, address: int) -> dict:
        """模拟读取单个寄存器"""
        if address in self.registers:
            name, min_v, max_v, unit = self.registers[address]
            noise = random.uniform(0.95, 1.05)
            val = self.current_values[address] * noise
            self.current_values[address] = val
            return {"address": address, "name": name, "value": round(val, 2), "unit": unit}
        return {"address": address, "error": "无效地址"}

    def read_all(self) -> list:
        """模拟一次批量采集（循环读取所有仪表）"""
        results = []
        for addr in self.registers:
            results.append(self.read_register(addr))
        return results

    def map_to_energy(self, readings: list) -> dict:
        """将 MODBUS 读数映射为碳排放系统可用的能源数据"""
        mapping = {
            "主变电表_总用电量": "电网电力",
            "车间1_电表": "电网电力",
            "车间2_电表": "电网电力",
            "天然气总流量计": "天然气",
            "天然气_锅炉房": "天然气",
            "煤仓_皮带秤": "烟煤",
            "柴油_地磅": "柴油",
        }
        energy_usage = {}
        for r in readings:
            if "error" in r:
                continue
            name = r["name"]
            fuel = mapping.get(name)
            if fuel:
                if fuel not in energy_usage:
                    energy_usage[fuel] = 0
                energy_usage[fuel] += r["value"]
        return energy_usage


# ============================================
# 自动采集器（定时任务）
# ============================================
class AutoCollector:
    """自动数据采集器 —— 模拟工厂 IoT 网关"""

    def __init__(self, interval_seconds: int = 60):
        self.modbus = ModbusSimulator()
        self.interval = interval_seconds
        self.running = False
        self.collected_data = []
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "iot")

    def start(self):
        """启动定时采集（后台线程）"""
        self.running = True
        Thread(target=self._loop, daemon=True).start()
        print(f"IoT 采集器已启动，间隔 {self.interval} 秒")

    def _loop(self):
        while self.running:
            readings = self.modbus.read_all()
            energy = self.modbus.map_to_energy(readings)
            record = {
                "timestamp": datetime.now().isoformat(),
                "raw_readings": readings,
                "energy_usage": energy,
            }
            self.collected_data.append(record)

            # 定期保存到本地
            if len(self.collected_data) % 60 == 0:
                self.save()

            time.sleep(self.interval)

    def save(self):
        """保存采集数据"""
        os.makedirs(self.data_dir, exist_ok=True)
        from pandas import DataFrame
        records = []
        for rec in self.collected_data:
            for fuel, val in rec["energy_usage"].items():
                records.append({
                    "时间": rec["timestamp"],
                    "能源类型": fuel,
                    "活动数据": round(val, 3),
                    "数据单位": self.modbus.registers[0x0100][3],  # 单位
                })
        df = DataFrame(records)
        path = os.path.join(self.data_dir, f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")

    def stop(self):
        self.running = False

    def get_latest(self) -> dict:
        """获取最近一次采集的能源数据"""
        if not self.collected_data:
            self.modbus.read_all()
            readings = self.modbus.read_all()
            return self.modbus.map_to_energy(readings)
        return self.collected_data[-1]["energy_usage"]

    def get_status(self) -> dict:
        """获取仪表状态（用于显示在线/离线）"""
        status = {}
        for addr, (name, _, _, unit) in self.modbus.registers.items():
            # 模拟仪表状态（90% 在线）
            online = random.random() > 0.1
            val = self.modbus.current_values.get(addr, 0)
            status[name] = {
                "value": round(val, 2),
                "unit": unit,
                "online": online,
                "last_update": datetime.now().isoformat() if online else "离线",
            }
        return status


# ============================================
# 测试
# ============================================
if __name__ == "__main__":
    modbus = ModbusSimulator()
    print("=== MODBUS 模拟器 单次采集 ===")
    readings = modbus.read_all()
    for r in readings:
        if "error" in r:
            print(f"  ❌ 地址 {r['address']}: {r['error']}")
        else:
            print(f"  📡 [{r['name']}] {r['value']} {r['unit']}")

    print("\n=== 能源映射 ===")
    energy = modbus.map_to_energy(readings)
    for fuel, val in energy.items():
        print(f"  {fuel}: {val:.2f}")

    print("\n=== 自动采集器 ===")
    collector = AutoCollector(interval_seconds=2)
    print(f"  最近采集: {collector.get_latest()}")
    print(f"  仪表状态: {len(collector.get_status())} 个仪表")
