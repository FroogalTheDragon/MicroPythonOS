print("crowpanel_esp32s3_7.py initialization")
# Hardware initialization for Elecrow CrowPanel Advanced 7" ESP32-S3 IPS (v1.2+)
# Manufacturer reference: LovyanGFX_Driver.h from CrowPanel Advance example code
# Display: 7" 800x480 RGB parallel (16-bit RGB565)
# Touch: GT911, I2C on SDA=GPIO 15, SCL=GPIO 16
#
# NOTE: This is the CrowPanel Advance IPS board (v1.2+), NOT the original WZ8048C070.
# The Advance IPS board uses completely different GPIO pins for the RGB data bus.
# GPIO 15/16 are NOT part of the RGB data bus on this board (unlike WZ8048C070),
# so they are free for both the backlight expander and the touch controller I2C bus.

import lcd_bus
import lvgl as lv
import mpos.ui
import drivers.display.rgb_display as rgb_display
import drivers.indev.gt911 as gt911
from machine import I2C as _MachineI2C, SoftI2C as _SoftI2C, Pin as _Pin
from mpos import InputManager
from micropython import const

# ==============================
# Display pin configuration
# (from CrowPanel Advance 7" LovyanGFX_Driver.h, V1.0 example code)
# ==============================
LCD_WIDTH  = const(800)
LCD_HEIGHT = const(480)

LCD_PCLK  = const(39)
LCD_HSYNC = const(40)
LCD_VSYNC = const(41)
LCD_DE    = const(42)
LCD_BL    = const(2)   # PWM backlight

# Blue channel B0-B4
LCD_B0 = const(21)
LCD_B1 = const(47)
LCD_B2 = const(48)
LCD_B3 = const(45)
LCD_B4 = const(38)

# Green channel G0-G5
LCD_G0 = const(9)
LCD_G1 = const(10)
LCD_G2 = const(11)
LCD_G3 = const(12)
LCD_G4 = const(13)
LCD_G5 = const(14)

# Red channel R0-R4
LCD_R0 = const(7)
LCD_R1 = const(17)
LCD_R2 = const(18)
LCD_R3 = const(3)
LCD_R4 = const(46)

# Touch and backlight expander — both on GPIO 15/16 (NOT used by RGB bus on Advance board)
TOUCH_SDA  = const(15)
TOUCH_SCL  = const(16)
TOUCH_ADDR = const(0x5D)  # GT911 default when INT is HIGH at power-up (Advance board)

BL_EXPANDER_CMD  = const(0x10)

# ==============================
# Step 1: Enable backlight via IO expander
# GPIO 15/16 are safe to use here — they are NOT part of the RGB data bus on this board.
# Both 0x30 (standard) and 0x51 (HW v1.4) respond on this bus; write to both.
# ==============================
print("crowpanel_esp32s3_7.py enabling backlight expander")
_bl_i2c = _MachineI2C(1, scl=_Pin(TOUCH_SCL), sda=_Pin(TOUCH_SDA), freq=400000)
for _addr in (0x30, 0x51):
    try:
        _bl_i2c.writeto(_addr, bytes([BL_EXPANDER_CMD]))
        print(f"crowpanel_esp32s3_7.py backlight expander 0x{_addr:02X} OK")
    except Exception as e:
        print(f"crowpanel_esp32s3_7.py WARNING: backlight expander 0x{_addr:02X} failed: {e}")
del _bl_i2c

# ==============================
# Step 2: RGB display bus
# Timing from CrowPanel Advance 7" LovyanGFX_Driver.h (V1.0 example):
#   hsync_front_porch=8, hsync_pulse_width=4, hsync_back_porch=8
#   vsync_front_porch=8, vsync_pulse_width=4, vsync_back_porch=8
#   pclk_idle_high=1, freq=21MHz
# ==============================
print("crowpanel_esp32s3_7.py init RGB display bus")
display_bus = lcd_bus.RGBBus(
    hsync=LCD_HSYNC,
    vsync=LCD_VSYNC,
    de=LCD_DE,
    pclk=LCD_PCLK,
    data0=LCD_B0,
    data1=LCD_B1,
    data2=LCD_B2,
    data3=LCD_B3,
    data4=LCD_B4,
    data5=LCD_G0,
    data6=LCD_G1,
    data7=LCD_G2,
    data8=LCD_G3,
    data9=LCD_G4,
    data10=LCD_G5,
    data11=LCD_R0,
    data12=LCD_R1,
    data13=LCD_R2,
    data14=LCD_R3,
    data15=LCD_R4,
    freq=16000000,
    hsync_front_porch=8,
    hsync_back_porch=8,
    hsync_pulse_width=4,
    hsync_idle_low=False,
    vsync_front_porch=8,
    vsync_back_porch=8,
    vsync_pulse_width=4,
    vsync_idle_low=False,
    de_idle_high=False,
    pclk_idle_high=False,
    pclk_active_low=True,
)

# Allocate full-frame PSRAM framebuffers (analogous to LovyanGFX use_psram=1).
# Full-frame mode avoids the partial-flush tearing/scrolling that occurs when
# the ESP-IDF RGB DMA displays partially-updated buffers mid-frame.
_FB_SIZE = LCD_WIDTH * LCD_HEIGHT * 2  # RGB565: 2 bytes/pixel = 768 KB
_fb1 = display_bus.allocate_framebuffer(_FB_SIZE, lcd_bus.MEMORY_SPIRAM)
_fb2 = display_bus.allocate_framebuffer(_FB_SIZE, lcd_bus.MEMORY_SPIRAM)
print(f"crowpanel_esp32s3_7.py framebuffers: {_FB_SIZE} bytes each in SPIRAM")

mpos.ui.main_display = rgb_display.RGBDisplay(
    data_bus=display_bus,
    display_width=LCD_WIDTH,
    display_height=LCD_HEIGHT,
    frame_buffer1=_fb1,
    frame_buffer2=_fb2,
    color_space=lv.COLOR_FORMAT.RGB565,
    color_byte_order=rgb_display.BYTE_ORDER_RGB,
    rgb565_byte_swap=False,
    backlight_pin=LCD_BL,
    backlight_on_state=rgb_display.STATE_HIGH,
)
mpos.ui.main_display.init()
mpos.ui.main_display.set_power(True)
mpos.ui.main_display.set_backlight(100)

# Quick display test: paint screen RED and force a render cycle
_test_scr = lv.screen_active()
_test_scr.set_style_bg_color(lv.color_make(255, 0, 0), 0)
_test_scr.set_style_bg_opa(255, 0)
_test_label = lv.label(_test_scr)
_test_label.set_text("crowpanel_esp32s3_7 display test")
_test_label.set_style_text_color(lv.color_make(255, 255, 255), 0)
_test_label.center()
lv.refr_now(None)
print("crowpanel_esp32s3_7.py display test rendered (red background)")

# ==============================
# Step 3: GT911 touch controller
# GPIO 15/16 are not used by the RGB bus on the Advance board, so touch and the
# backlight expander share the same physical I2C bus without conflict.
# SoftI2C is used to avoid GDMA channel conflicts with the RGB LCD peripheral.
# ==============================
print("crowpanel_esp32s3_7.py init GT911 touch")

class _MachineI2CDevice:
    """machine.I2C / SoftI2C adapter matching the write_mem/write_readinto interface GT911 expects."""
    def __init__(self, i2c_bus, addr):
        self._bus = i2c_bus
        self._addr = addr

    def write_mem(self, reg, buf):
        payload = bytearray(2 + len(buf))
        payload[0] = (reg >> 8) & 0xFF
        payload[1] = reg & 0xFF
        payload[2:] = buf
        self._bus.writeto(self._addr, payload)

    def write_readinto(self, write_buf, read_buf):
        reg = (write_buf[0] << 8) | write_buf[1]
        self._bus.readfrom_mem_into(self._addr, reg, read_buf, addrsize=16)

_touch_i2c = _SoftI2C(scl=_Pin(TOUCH_SCL), sda=_Pin(TOUCH_SDA), freq=100000)
_scan = _touch_i2c.scan()
print(f"Touch I2C scan: {[hex(a) for a in _scan]}")
touch_dev = _MachineI2CDevice(_touch_i2c, TOUCH_ADDR)
indev = gt911.GT911(touch_dev, startup_rotation=lv.DISPLAY_ROTATION._0)
InputManager.register_indev(indev)

# Must be set after both display and touch are initialised
mpos.ui.main_display.set_rotation(lv.DISPLAY_ROTATION._0)

print("crowpanel_esp32s3_7.py finished")
