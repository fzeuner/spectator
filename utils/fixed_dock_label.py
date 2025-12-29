from pyqtgraph.dockarea.Dock import DockLabel


class FixedDockLabel(DockLabel):
    def __init__(self, *args, min_thickness: int = 22, **kwargs):
        super().__init__(*args, **kwargs)
        self._min_thickness = int(min_thickness)
        try:
            self.forceWidth = True
        except Exception:
            pass

    def paintEvent(self, ev):
        super().paintEvent(ev)
        mt = self._min_thickness
        try:
            self.setMinimumWidth(mt)
            self.setMinimumHeight(mt)
        except Exception:
            pass
