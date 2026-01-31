


import sys

import pytest

from PySide6.QtCore import QPoint, QRect, Qt

from PySide6.QtGui import QPixmap, QPainter, QColor

from PySide6.QtWidgets import QApplication



# Add the parent directory to the path to allow module imports

sys.path.insert(0, '.')



from capture import CaptureWindow



@pytest.fixture(scope="session")

def app_instance():

    """Ensure a single QApplication instance exists for the test session."""

    app = QApplication.instance()

    if app is None:

        app = QApplication(sys.argv)

    return app



def test_capture_window_init(app_instance, qtbot):

    """Test that the capture window initializes correctly."""

    widget = CaptureWindow()

    qtbot.add_widget(widget)

    

    assert widget.isWindow()

    assert widget.windowFlags() & Qt.FramelessWindowHint

    assert widget.windowFlags() & Qt.WindowStaysOnTopHint

    assert widget.cursor().shape() == Qt.CrossCursor



def test_capture_simulation(app_instance, qtbot):

    """

    Test the full capture sequence by simulating mouse movements

    and verifying the emitted signal's pixmap size.

    

    Note: On high-DPI displays, the captured pixmap size is in physical pixels,

    which is the logical size multiplied by devicePixelRatio.

    """

    widget = CaptureWindow()

    qtbot.add_widget(widget)

    widget.show()



    # Define the capture area (logical pixels)

    start_pos = QPoint(50, 50)

    end_pos = QPoint(150, 150)

    logical_rect = QRect(start_pos, end_pos)

    

    with qtbot.wait_signal(widget.screenshot_completed, timeout=1000) as blocker:

        qtbot.mousePress(widget, Qt.LeftButton, pos=start_pos)

        qtbot.mouseMove(widget, pos=end_pos)

        qtbot.mouseRelease(widget, Qt.LeftButton, pos=end_pos)



    # Check the signal's payload (the captured pixmap)

    assert blocker.signal_triggered

    captured_pixmap = blocker.args[0]

    

    assert isinstance(captured_pixmap, QPixmap)

    assert not captured_pixmap.isNull()

    

    # On high-DPI displays, the physical pixmap size should be scaled by devicePixelRatio

    dpr = captured_pixmap.devicePixelRatio()

    expected_physical_size = logical_rect.size() * dpr

    assert captured_pixmap.rect().size() == expected_physical_size



def test_capture_coordinate_accuracy(app_instance, qtbot):

    """

    Test that the captured region perfectly matches the selected coordinates

    by checking the color of pixels in the captured image.

    """

    # 1. Create a "virtual screen" with a known pattern

    screen_size = QRect(0, 0, 400, 400)

    virtual_screen = QPixmap(screen_size.size())

    virtual_screen.fill(Qt.blue) # Fill with a base color



    # 2. Draw a marker at a known position

    marker_rect = QRect(100, 100, 10, 10)

    marker_color = QColor("red")

    painter = QPainter(virtual_screen)

    painter.fillRect(marker_rect, marker_color)

    painter.end()



    # 3. Inject the virtual screen into the capture widget

    widget = CaptureWindow()

    qtbot.add_widget(widget)

    widget._background_pixmap = virtual_screen

    widget.setGeometry(screen_size)

    widget.show()



    # 4. Simulate a capture around the marker

    start_pos = QPoint(75, 75)

    end_pos = QPoint(175, 175) # A 100x100 selection

    

    with qtbot.wait_signal(widget.screenshot_completed, timeout=1000) as blocker:

        qtbot.mousePress(widget, Qt.LeftButton, pos=start_pos)

        qtbot.mouseMove(widget, pos=end_pos)

        qtbot.mouseRelease(widget, Qt.LeftButton, pos=end_pos)



    # 5. Verify the pixels in the resulting image

    assert blocker.signal_triggered

    captured_pixmap = blocker.args[0]

    assert captured_pixmap.size() == QRect(start_pos, end_pos).size()



    captured_image = captured_pixmap.toImage()

    

    # The marker was at (100, 100) on the virtual screen.

    # The capture started at (75, 75).

    # So, the marker should start at (100-75, 100-75) = (25, 25) in the captured image.

    pixel_color = captured_image.pixelColor(25, 25)

    assert pixel_color == marker_color, "Pixel color at marker position is incorrect"



    # Check a pixel that should be part of the background

    background_pixel_color = captured_image.pixelColor(10, 10)

    assert background_pixel_color == QColor("blue"), "Pixel color of background is incorrect"





def test_capture_escape_key(app_instance, qtbot):

    """Test that pressing the 'Esc' key closes the widget."""

    widget = CaptureWindow()

    qtbot.add_widget(widget)

    widget.show()

    

    assert widget.isVisible()

    

    # Simulate pressing the Escape key

    qtbot.keyClick(widget, Qt.Key_Escape)

    

    # The widget should be closed (not visible)

    assert not widget.isVisible()



