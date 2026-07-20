"""Tool: system operations — run_shell, system_status, take_screenshot."""
import subprocess
from pathlib import Path

TOOLS = [
    ("run_shell", "\u6267\u884cPowerShell\u547d\u4ee4", {"command": ("string", "\u547d\u4ee4")}, ["command"]),
    ("system_status", "\u67e5\u770b\u7cfb\u7edf\u72b6\u6001", {}, []),
    ("take_screenshot", "\u622a\u53d6\u5c4f\u5e55\u622a\u56fe", {"filename": ("string", "\u6587\u4ef6\u540d")}, []),
]


def _run_shell(args):
    command = args.get("command", "")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + command],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace", creationflags=0x08000000
        )
        out = r.stdout.strip() or r.stderr.strip()
        return out[:3000] if out else "(\u65e0\u8f93\u51fa)"
    except subprocess.TimeoutExpired:
        return "\u547d\u4ee4\u8d85\u65f6"


def _system_status(args):
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:/")
        return f"CPU: {cpu}% | \u5185\u5b58: {mem.percent}% | \u78c1\u76d8C: {disk.percent}% ({disk.free//(1024**3)}GB\u7a7a\u95f2)"
    except ImportError:
        # psutil 不在 requirements 中时走 PowerShell 兜底（已列入 requirements 所以极少触发）
        r = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
             "(Get-CimInstance Win32_Processor).LoadPercentage;"
             "$os=Get-CimInstance Win32_OperatingSystem;"
             "\"{0}/{1}\" -f [math]::Round($os.FreePhysicalMemory/1MB,1),[math]::Round($os.TotalVisibleMemorySize/1MB,1);"
             "$d=Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\";[math]::Round($d.FreeSpace/1GB,1)"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        lines = r.stdout.strip().split("\n")
        cpu_str = f"{lines[0]}%" if len(lines) > 0 and lines[0] else "?"
        mem_str = lines[1] if len(lines) > 1 and lines[1] else "?"
        disk_str = lines[2] if len(lines) > 2 and lines[2] else "?"
        return f"CPU: {cpu_str} | \u5185\u5b58: {mem_str}MB | \u78c1\u76d8C: {disk_str}GB\u7a7a\u95f2"


def _take_screenshot(args):
    filename = args.get("filename", "screenshot.png")
    desktop = Path.home() / "Desktop"
    p = desktop / (filename if "." in filename else filename + ".png")
    try:
        from PIL import ImageGrab
        ImageGrab.grab().save(str(p), "PNG")
        return f"\u622a\u56fe\u5df2\u4fdd\u5b58: {p.name}"
    except ImportError:
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
             "Add-Type -AssemblyName System.Windows.Forms;"
             f"$img=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
             f"$bmp=New-Object System.Drawing.Bitmap($img.Width,$img.Height);"
             f"$g=[System.Drawing.Graphics]::FromImage($bmp);"
             f"$g.CopyFromScreen(0,0,0,0,$img.Size);"
             f"$bmp.Save('{p}');$g.Dispose();$bmp.Dispose()"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        return f"\u622a\u56fe\u5df2\u4fdd\u5b58: {p.name}" if p.exists() else "\u622a\u56fe\u5931\u8d25"


HANDLERS = {
    "run_shell": _run_shell,
    "system_status": _system_status,
    "take_screenshot": _take_screenshot,
}
