import sys
import threading
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import frida
import memio
import logging
import os

logging.basicConfig(
    filename='debug_reader.log', 
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("Target Block UI Started")

FRIDA_SCRIPT = """
const baseAddr = Process.getModuleByName('HytaleClient.exe').base;
let lastPosX = 0, lastPosY = 0, lastPosZ = 0;
let lastTx = 0, lastTy = 0, lastTz = 0;

if (baseAddr) {
    // 1. Hook the Target Block Read Function
    const targetHook = baseAddr.add(0x6F31AE);
    Interceptor.attach(targetHook, {
        onEnter: function(args) {
            try {
                let rcx = this.context.rcx;
                
                let tx = Math.floor(rcx.readFloat());
                let ty = Math.floor(rcx.add(4).readFloat());
                let tz = Math.floor(rcx.add(8).readFloat());
                
                // Spam filter to prevent crashes
                if ((tx !== lastTx || ty !== lastTy || tz !== lastTz) && 
                    tx > -30000 && tx < 30000 && ty >= 0 && ty <= 256 && tz > -30000 && tz < 30000) {
                    lastTx = tx; lastTy = ty; lastTz = tz;
                    send({
                        t: 'target', 
                        tx: tx, ty: ty, tz: tz, tid: 0, ints: []
                    });
                }
            } catch (e) {}
        }
    });

    // 2. Hook the new Player Position read function!
    let lastPosTime = 0;
    const posHook = baseAddr.add(0x42808C);
    Interceptor.attach(posHook, {
        onEnter: function(args) {
            try {
                let now = Date.now();
                if (now - lastPosTime > 100) {
                    lastPosTime = now;
                    
                    let rbx = this.context.rbx;
                    let posX = rbx.add(0x24).readFloat();
                    let posY = rbx.add(0x28).readFloat();
                    let posZ = rbx.add(0x2C).readFloat();
                    
                    let pitchRad = rbx.add(0x3C).readFloat();
                    let yawRad = rbx.add(0x40).readFloat();
                    let pitchDeg = pitchRad * (180.0 / Math.PI);
                    let yawDeg = yawRad * (180.0 / Math.PI);
                    
                    send({
                        t: 'pos', 
                        px: Math.floor(posX), py: Math.floor(posY), pz: Math.floor(posZ),
                        pitch: pitchDeg, yaw: yawDeg,
                        tid: 0, floats: []
                    });
                }
            } catch (e) {}
        }
    });
}
send({t: 'info', msg: "Both Position and Target Block are now Automatically Hooked!"});
"""

class SignalBridge(QObject):
    log_signal = pyqtSignal(str)
    pos_signal = pyqtSignal(int, int, int, int, list, float, float)
    target_signal = pyqtSignal(int, int, int, int, list)

class TargetBlockUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hytale Target Block")
        
        # Make it always on top and frameless for a nice overlay feel
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(550, 400)
        
        self.bridge = SignalBridge()
        self.bridge.log_signal.connect(self.log_msg)
        self.bridge.pos_signal.connect(self.update_pos)
        self.bridge.target_signal.connect(self.update_target)
        
        self.init_ui()
        
        self.session = None
        self.script = None
        
        threading.Thread(target=self.run_frida, daemon=True).start()

    def init_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: rgba(20, 20, 20, 200); border-radius: 15px; border: 2px solid #555;")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 10, 15, 15)
        
        self.lbl_status = QLabel("Waiting for game...")
        self.lbl_status.setStyleSheet("color: #aaaaaa; font-family: 'Segoe UI'; font-size: 13px; border: none; background: transparent;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)
        
        self.lbl_pos = QLabel("Position: (None)")
        self.lbl_pos.setStyleSheet("color: #00ff66; font-family: 'Consolas'; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        self.lbl_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_pos)
        
        self.lbl_target = QLabel("Target Block: (None)")
        self.lbl_target.setStyleSheet("color: #00ff66; font-family: 'Consolas'; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        self.lbl_target.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_target)

        self.lbl_orient = QLabel("Orientation: (Looking...)")
        self.lbl_orient.setStyleSheet("color: #00ff66; font-family: 'Consolas'; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        self.lbl_orient.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_orient)

    # Allow dragging the frameless window around the screen
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'dragPos'):
            self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos)
            self.dragPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'dragPos'):
            del self.dragPos

    def log_msg(self, msg):
        logging.info(f"UI Status: {msg}")
        self.lbl_status.setText(msg)

    def update_pos(self, px, py, pz, tid, p_floats, pitch, yaw):
        self.lbl_pos.setText(f"Position: ({px}, {py}, {pz})")
        self.lbl_orient.setText(f"Orientation: ({pitch:.1f}°, {yaw:.1f}°, 0.0°)")

    def update_target(self, tx, ty, tz, tid, t_ints):
        self.last_tx = tx
        self.last_ty = ty
        self.last_tz = tz
        self.lbl_target.setText(f"Target Block: ({tx}, {ty}, {tz})")

    def run_frida(self):
        self.bridge.log_signal.emit("Searching for HytaleClient.exe...")
        pid = None
        while not pid:
            pid = memio.find_client_pid()
            if not pid:
                time.sleep(1)
                
        self.bridge.log_signal.emit(f"Attaching to PID {pid}...")
        try:
            self.session = frida.attach(pid)
        except Exception as e:
            self.bridge.log_signal.emit(f"Frida attach failed: {e}")
            return
            
        self.script = self.session.create_script(FRIDA_SCRIPT)
        
        def on_message(message, data):
            if message["type"] == "send":
                payload = message.get("payload", {})
                if payload.get("t") == "info" or payload.get("t") == "error":
                    logging.info(f"Frida: {payload.get('msg')}")
                    self.bridge.log_signal.emit(payload.get("msg"))
                elif payload.get("t") == "pos":
                    self.bridge.pos_signal.emit(
                        payload.get("px"), payload.get("py"), payload.get("pz"),
                        payload.get("tid"), payload.get("floats", []),
                        payload.get("pitch", 0.0), payload.get("yaw", 0.0)
                    )
                elif payload.get("t") == "target":
                    self.bridge.target_signal.emit(
                        payload.get("tx"), payload.get("ty"), payload.get("tz"), payload.get("tid"), payload.get("ints", [])
                    )
            elif message["type"] == "error":
                logging.error(f"Frida Error: {message.get('description')}")
                self.bridge.log_signal.emit(f"Frida Error: {message.get('description')}")
                
        self.script.on("message", on_message)
        self.script.load()
        
        # Keep alive loop
        while True:
            time.sleep(1)

def main():
    app = QApplication(sys.argv)
    window = TargetBlockUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
