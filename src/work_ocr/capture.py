
import sys
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QGuiApplication, QPixmap
from PySide6.QtCore import Qt, QRect, Signal

class CaptureWindow(QWidget):
    """
    A semi-transparent window for capturing a region of the screen.
    Emits a 'screenshot_completed' signal with the captured QPixmap when done.
    Emits a 'screenshot_cancelled' signal when user cancels the capture.
    """
    screenshot_completed = Signal(QPixmap)
    screenshot_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        # 获取主屏幕信息和虚拟几何
        self._screen = QGuiApplication.primaryScreen()
        
        # 使用虚拟几何设置窗口大小，支持多显示器
        virtual_geometry = self._screen.virtualGeometry()
        self.setGeometry(virtual_geometry)

        # 捕获整个虚拟桌面
        self._background_pixmap = self._screen.grabWindow(
            0,
            virtual_geometry.x(),
            virtual_geometry.y(),
            virtual_geometry.width(),
            virtual_geometry.height()
        )
        
        self._is_selecting = False
        self._start_point = None
        self._end_point = None
        self._selection_rect = QRect()

    def keyPressEvent(self, event):
        """Close the window and emit cancelled signal when the 'Esc' key is pressed."""
        if event.key() == Qt.Key_Escape:
            self.screenshot_cancelled.emit()
            self.close()
            event.accept()

    def mousePressEvent(self, event):
        """Start selecting a region when the left mouse button is pressed."""
        if event.button() == Qt.LeftButton:
            self._is_selecting = True
            self._start_point = event.position().toPoint()
            self._end_point = self._start_point
            self.update()  # Trigger a repaint
            event.accept()

    def mouseMoveEvent(self, event):
        """Update the selection region as the mouse moves."""
        if self._is_selecting:
            self._end_point = event.position().toPoint()
            self.update()  # Trigger a repaint
            event.accept()

    def mouseReleaseEvent(self, event):
        """Finalize the selection and emit the captured pixmap."""
        if event.button() == Qt.LeftButton and self._is_selecting:
            self._is_selecting = False
            self.close()  # Close the capture window

            capture_rect = self.get_normalized_selection()
            if capture_rect.isValid() and capture_rect.width() > 5 and capture_rect.height() > 5:
                # 使用背景图片的 devicePixelRatio 进行坐标转换
                # 这对于支持高 DPI 显示器和测试环境都很重要
                dpr = self._background_pixmap.devicePixelRatio()
                physical_rect = QRect(
                    int(capture_rect.x() * dpr),
                    int(capture_rect.y() * dpr),
                    int(capture_rect.width() * dpr),
                    int(capture_rect.height() * dpr)
                )
                captured_pixmap = self._background_pixmap.copy(physical_rect)
                self.screenshot_completed.emit(captured_pixmap)
            else:
                # Selection too small, treat as cancelled
                self.screenshot_cancelled.emit()
            event.accept()

    def paintEvent(self, event):
        """Draw the semi-transparent overlay and the selection rectangle."""
        painter = QPainter(self)
        
        # Draw the semi-transparent background
        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)

        if self._is_selecting:
            self._selection_rect = self.get_normalized_selection()
            
            # Clear the selected area (make it fully transparent)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self._selection_rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw the border of the selection rectangle
            pen = QPen(QColor(0, 120, 215), 2)  # A blueish color
            painter.setPen(pen)
            painter.drawRect(self._selection_rect)

    def get_normalized_selection(self):
        """Returns a QRect with positive width and height."""
        return QRect(self._start_point, self._end_point).normalized()

def main():
    """
    A simple test function to demonstrate the CaptureWindow.
    Saves the captured image to 'capture_test.png'.
    """
    app = QApplication(sys.argv)
    
    capture_widget = CaptureWindow()

    def on_capture_finished(pixmap):
        print("Capture finished!")
        if not pixmap.isNull():
            pixmap.save("capture_test.png")
            print("Saved captured image to capture_test.png")
        app.quit()
    
    # Connect the signal to the slot and show the widget
    capture_widget.screenshot_completed.connect(on_capture_finished)
    # The window should close itself when Esc is pressed or capture is done
    capture_widget.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
